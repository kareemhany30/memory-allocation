from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hole:
    start: int
    size: int

    @property
    def end(self) -> int:
        return self.start + self.size


@dataclass(frozen=True)
class SegmentPlacement:
    process_name: str
    segment_name: str
    start: int
    size: int

    @property
    def end(self) -> int:
        return self.start + self.size


@dataclass(frozen=True)
class MemoryBlock:
    start: int
    size: int
    label: str
    kind: str

    @property
    def end(self) -> int:
        return self.start + self.size


class AllocationError(ValueError):
    """Raised when a process cannot be fully allocated."""


class MemoryManager:
    def __init__(self, total_size: int = 1024) -> None:
        self.total_size = total_size
        self.holes: list[Hole] = []
        self.allocations: dict[str, list[SegmentPlacement]] = {}

    def configure_memory(self, total_size: int, holes: list[Hole]) -> None:
        if total_size <= 0:
            raise ValueError("Total memory size must be positive.")

        cleaned = self._validate_holes(total_size, holes)
        self.total_size = total_size
        self.holes = cleaned
        self.allocations.clear()

    def allocate_process(
        self,
        process_name: str,
        segments: list[tuple[str, int]],
        method: str,
    ) -> list[SegmentPlacement]:
        process_name = process_name.strip()
        if not process_name:
            raise ValueError("Process name is required.")
        if process_name in self.allocations:
            raise ValueError(f"{process_name} is already allocated.")
        if not segments:
            raise ValueError("Add at least one segment before allocation.")

        normalized: list[tuple[str, int]] = []
        for segment_name, size in segments:
            segment_name = segment_name.strip()
            if not segment_name:
                raise ValueError("Segment name is required.")
            if size <= 0:
                raise ValueError("Segment size must be positive.")
            normalized.append((segment_name, size))

        method = method.lower().replace("-", "_").strip()
        if method not in {"first_fit", "best_fit"}:
            raise ValueError("Allocation method must be First-Fit or Best-Fit.")

        temp_holes = list(self.holes)
        placements: list[SegmentPlacement] = []

        for segment_name, size in normalized:
            hole_index = self._select_hole(temp_holes, size, method)
            if hole_index is None:
                raise AllocationError(
                    f"{process_name} does not fit. Segment {segment_name} needs {size} bytes."
                )

            hole = temp_holes[hole_index]
            placements.append(
                SegmentPlacement(
                    process_name=process_name,
                    segment_name=segment_name,
                    start=hole.start,
                    size=size,
                )
            )

            remaining = hole.size - size
            if remaining == 0:
                temp_holes.pop(hole_index)
            else:
                temp_holes[hole_index] = Hole(hole.start + size, remaining)

        self.holes = self._merge_holes(temp_holes)
        self.allocations[process_name] = placements
        return placements

    def deallocate_process(self, process_name: str) -> list[SegmentPlacement]:
        if process_name not in self.allocations:
            raise ValueError(f"{process_name} is not allocated.")

        placements = self.allocations.pop(process_name)
        released = [Hole(item.start, item.size) for item in placements]
        self.holes = self._merge_holes([*self.holes, *released])
        return placements

    def all_segments(self) -> list[SegmentPlacement]:
        segments: list[SegmentPlacement] = []
        for process_segments in self.allocations.values():
            segments.extend(process_segments)
        return sorted(segments, key=lambda item: item.start)

    def process_names(self) -> list[str]:
        return sorted(self.allocations)

    def snapshot(self) -> list[MemoryBlock]:
        blocks: list[MemoryBlock] = []

        for hole in self.holes:
            blocks.append(MemoryBlock(hole.start, hole.size, "Free hole", "hole"))

        for segment in self.all_segments():
            blocks.append(
                MemoryBlock(
                    segment.start,
                    segment.size,
                    f"{segment.process_name}:{segment.segment_name}",
                    "segment",
                )
            )

        blocks.sort(key=lambda item: item.start)
        completed: list[MemoryBlock] = []
        cursor = 0
        for block in blocks:
            if block.start > cursor:
                completed.append(
                    MemoryBlock(cursor, block.start - cursor, "Reserved", "reserved")
                )
            completed.append(block)
            cursor = max(cursor, block.end)

        if cursor < self.total_size:
            completed.append(MemoryBlock(cursor, self.total_size - cursor, "Reserved", "reserved"))

        return completed

    def _select_hole(self, holes: list[Hole], size: int, method: str) -> int | None:
        candidates = [(index, hole) for index, hole in enumerate(holes) if hole.size >= size]
        if not candidates:
            return None

        if method == "first_fit":
            return candidates[0][0]

        return min(candidates, key=lambda item: item[1].size)[0]

    def _validate_holes(self, total_size: int, holes: list[Hole]) -> list[Hole]:
        if not holes:
            return []

        ordered = sorted(holes, key=lambda item: item.start)
        previous_end = 0
        for hole in ordered:
            if hole.start < 0:
                raise ValueError("Hole start address cannot be negative.")
            if hole.size <= 0:
                raise ValueError("Hole size must be positive.")
            if hole.end > total_size:
                raise ValueError("A hole extends beyond total memory size.")
            if hole.start < previous_end:
                raise ValueError("Holes cannot overlap.")
            previous_end = hole.end

        return self._merge_holes(ordered)

    def _merge_holes(self, holes: list[Hole]) -> list[Hole]:
        ordered = sorted(holes, key=lambda item: item.start)
        merged: list[Hole] = []

        for hole in ordered:
            if not merged or merged[-1].end < hole.start:
                merged.append(hole)
                continue

            previous = merged[-1]
            merged[-1] = Hole(previous.start, max(previous.end, hole.end) - previous.start)

        return merged
