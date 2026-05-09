from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pygame

from memory_allocator import AllocationError, Hole, MemoryManager


WIDTH = 1240
HEIGHT = 760
FPS = 60

BG = (246, 247, 250)
PANEL = (255, 255, 255)
INK = (28, 35, 45)
MUTED = (98, 107, 120)
LINE = (213, 218, 226)
BLUE = (45, 102, 204)
GREEN = (31, 143, 96)
RED = (197, 67, 67)
YELLOW = (240, 184, 69)
VIOLET = (118, 86, 184)
RESERVED = (179, 184, 194)


def color_for_process(name: str) -> tuple[int, int, int]:
    palette = [
        (45, 102, 204),
        (31, 143, 96),
        (216, 122, 42),
        (118, 86, 184),
        (200, 77, 112),
        (37, 139, 154),
    ]
    return palette[sum(ord(ch) for ch in name) % len(palette)]


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: str
    fill: tuple[int, int, int] = BLUE
    enabled: bool = True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        fill = self.fill if self.enabled else (178, 184, 194)
        pygame.draw.rect(surface, fill, self.rect, border_radius=6)
        label = font.render(self.text, True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=self.rect.center))

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.enabled and self.rect.collidepoint(pos)


class TextInput:
    def __init__(self, rect: pygame.Rect, placeholder: str, value: str = "") -> None:
        self.rect = rect
        self.placeholder = placeholder
        self.value = value
        self.active = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        border = BLUE if self.active else LINE
        pygame.draw.rect(surface, (255, 255, 255), self.rect, border_radius=5)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=5)
        text = self.value if self.value else self.placeholder
        color = INK if self.value else (145, 151, 162)
        label = font.render(text, True, color)
        surface.blit(label, (self.rect.x + 10, self.rect.y + 9))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return self.active

        if event.type != pygame.KEYDOWN or not self.active:
            return False

        if event.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_TAB):
            self.active = False
        elif event.unicode and len(self.value) < 24:
            self.value += event.unicode
        return True


class MemoryAllocationApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Memory Allocation using Segmentation")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Segoe UI", 16)
        self.small = pygame.font.SysFont("Segoe UI", 13)
        self.bold = pygame.font.SysFont("Segoe UI Semibold", 18)
        self.title = pygame.font.SysFont("Segoe UI Semibold", 24)

        self.manager = MemoryManager(1024)
        self.pending_holes: list[Hole] = [Hole(0, 1024)]
        self.pending_segments: list[tuple[str, int]] = []
        self.method = "first_fit"
        self.status = "Enter holes, add process segments, then allocate."
        self.status_color = MUTED

        self.inputs = {
            "total": TextInput(pygame.Rect(24, 122, 118, 38), "Total", "1024"),
            "hole_start": TextInput(pygame.Rect(24, 202, 82, 38), "Start"),
            "hole_size": TextInput(pygame.Rect(116, 202, 82, 38), "Size"),
            "process": TextInput(pygame.Rect(24, 466, 174, 38), "Process name", "P1"),
            "segment": TextInput(pygame.Rect(24, 552, 98, 38), "Segment"),
            "segment_size": TextInput(pygame.Rect(132, 552, 66, 38), "Size"),
        }

    def run(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.handle_event(event)

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def handle_event(self, event: pygame.event.Event) -> None:
        for field in self.inputs.values():
            field.handle_event(event)

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        for button in self.buttons():
            if button.hit(event.pos):
                self.handle_action(button.action)
                return

    def handle_action(self, action: str) -> None:
        try:
            if action == "add_hole":
                self.add_hole()
            elif action == "reset_memory":
                self.reset_memory()
            elif action == "clear_holes":
                self.pending_holes.clear()
                self.status_ok("Hole list cleared. Add the free partitions.")
            elif action == "first_fit":
                self.method = "first_fit"
            elif action == "best_fit":
                self.method = "best_fit"
            elif action == "add_segment":
                self.add_segment()
            elif action == "clear_segments":
                self.pending_segments.clear()
                self.status_ok("Pending segments cleared.")
            elif action == "allocate":
                self.allocate()
            elif action.startswith("free:"):
                self.deallocate(action.split(":", 1)[1])
        except (ValueError, AllocationError) as exc:
            self.status_error(str(exc))

    def add_hole(self) -> None:
        start = self.parse_int("hole_start", "Hole start address", minimum=0)
        size = self.parse_int("hole_size", "Hole size", minimum=1)
        self.pending_holes.append(Hole(start, size))
        self.inputs["hole_start"].value = ""
        self.inputs["hole_size"].value = ""
        self.status_ok(f"Added hole at {start} with size {size}.")

    def reset_memory(self) -> None:
        total = self.parse_int("total", "Total memory size", minimum=1)
        self.manager.configure_memory(total, self.pending_holes)
        self.status_ok("Memory configured. Existing allocations were cleared.")

    def add_segment(self) -> None:
        name = self.inputs["segment"].value.strip()
        size = self.parse_int("segment_size", "Segment size", minimum=1)
        if not name:
            raise ValueError("Segment name is required.")
        self.pending_segments.append((name, size))
        self.inputs["segment"].value = ""
        self.inputs["segment_size"].value = ""
        self.status_ok(f"Added segment {name} ({size}).")

    def allocate(self) -> None:
        process = self.inputs["process"].value.strip()
        placements = self.manager.allocate_process(process, self.pending_segments, self.method)
        total = sum(item.size for item in placements)
        self.pending_segments.clear()
        self.inputs["process"].value = self.next_process_name()
        self.status_ok(f"Allocated {process} ({total} bytes) using {self.method_label()}.")

    def deallocate(self, process_name: str) -> None:
        self.manager.deallocate_process(process_name)
        self.status_ok(f"Deallocated all segments of {process_name} and merged holes.")

    def parse_int(self, input_name: str, label: str, minimum: int) -> int:
        value = self.inputs[input_name].value.strip()
        if not value:
            raise ValueError(f"{label} is required.")
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be a whole number.") from exc
        if number < minimum:
            raise ValueError(f"{label} must be at least {minimum}.")
        return number

    def next_process_name(self) -> str:
        index = 1
        names = set(self.manager.process_names())
        while f"P{index}" in names:
            index += 1
        return f"P{index}"

    def buttons(self) -> list[Button]:
        buttons = [
            Button(pygame.Rect(208, 202, 112, 38), "Add Hole", "add_hole", GREEN),
            Button(pygame.Rect(24, 252, 142, 36), "Apply Memory", "reset_memory", BLUE),
            Button(pygame.Rect(178, 252, 142, 36), "Clear Holes", "clear_holes", RED),
            Button(
                pygame.Rect(24, 382, 142, 38),
                "First-Fit",
                "first_fit",
                BLUE if self.method == "first_fit" else (123, 132, 145),
            ),
            Button(
                pygame.Rect(178, 382, 142, 38),
                "Best-Fit",
                "best_fit",
                BLUE if self.method == "best_fit" else (123, 132, 145),
            ),
            Button(pygame.Rect(208, 552, 112, 38), "Add Segment", "add_segment", GREEN),
            Button(pygame.Rect(24, 602, 142, 36), "Allocate", "allocate", BLUE),
            Button(pygame.Rect(178, 602, 142, 36), "Clear Segs", "clear_segments", RED),
        ]

        y = 704
        for process in self.manager.process_names():
            if y + 34 > 730:
                break
            buttons.append(Button(pygame.Rect(24, y, 296, 34), f"Deallocate {process}", f"free:{process}", VIOLET))
            y += 40
        return buttons

    def draw(self) -> None:
        self.screen.fill(BG)
        self.draw_header()
        self.draw_controls()
        self.draw_memory()
        self.draw_tables()

    def draw_header(self) -> None:
        self.screen.blit(self.title.render("Memory Allocation Project", True, INK), (24, 20))
        subtitle = "Segmentation simulator with First-Fit, Best-Fit, deallocation, and hole merging"
        self.screen.blit(self.font.render(subtitle, True, MUTED), (24, 51))

    def draw_controls(self) -> None:
        self.panel(pygame.Rect(16, 82, 316, 652))
        self.label("Memory setup", 24, 90, self.bold)
        self.inputs["total"].draw(self.screen, self.font)
        self.label("Pending holes", 24, 172, self.bold)
        self.inputs["hole_start"].draw(self.screen, self.font)
        self.inputs["hole_size"].draw(self.screen, self.font)

        for button in self.buttons():
            if button.rect.x < 340:
                button.draw(self.screen, self.font)

        hole_y = 300
        for hole in self.pending_holes[:2]:
            self.row_text(f"start {hole.start}", f"size {hole.size}", 24, hole_y)
            hole_y += 22
        if len(self.pending_holes) > 2:
            self.label(f"+ {len(self.pending_holes) - 2} more", 24, hole_y, self.small, MUTED)

        self.label("Allocation method", 24, 352, self.bold)
        self.label("Process", 24, 436, self.bold)
        self.inputs["process"].draw(self.screen, self.font)
        self.label("Segment builder", 24, 522, self.bold)
        self.inputs["segment"].draw(self.screen, self.font)
        self.inputs["segment_size"].draw(self.screen, self.font)

        y = 646
        for name, size in self.pending_segments[:1]:
            self.row_text(name, str(size), 24, y)
            y += 22
        if len(self.pending_segments) > 1:
            self.label(f"+ {len(self.pending_segments) - 1} more", 24, y, self.small, MUTED)

        self.label("Allocated processes", 24, 674, self.bold)
        if not self.manager.process_names():
            self.label("No active process yet", 24, 704, self.small, MUTED)

    def draw_memory(self) -> None:
        self.panel(pygame.Rect(348, 82, 390, 652))
        self.label("Memory layout", 364, 98, self.bold)
        self.label(f"Total: {self.manager.total_size} bytes", 600, 101, self.font, MUTED)

        x, y, w, h = 384, 140, 294, 548
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, w, h), border_radius=6)
        pygame.draw.rect(self.screen, LINE, (x, y, w, h), width=2, border_radius=6)

        total = max(1, self.manager.total_size)
        blocks = self.manager.snapshot()
        cursor_y = y
        for index, block in enumerate(blocks):
            raw_height = block.size / total * h
            block_height = max(16, int(raw_height)) if block.size > 0 else 0
            if index == len(blocks) - 1:
                block_height = y + h - cursor_y

            color = self.block_color(block)
            rect = pygame.Rect(x + 2, cursor_y, w - 4, max(1, block_height))
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.line(self.screen, (255, 255, 255), rect.topleft, rect.topright)

            label = f"{block.start}-{block.end}  {block.label} ({block.size})"
            text_color = (255, 255, 255) if block.kind == "segment" else INK
            self.screen.blit(self.small.render(label, True, text_color), (rect.x + 8, rect.y + 3))
            cursor_y += block_height

        self.status_box(pygame.Rect(364, 700, 350, 24))

    def draw_tables(self) -> None:
        self.panel(pygame.Rect(754, 82, 470, 652))
        self.label("Free partitions table", 772, 98, self.bold)
        self.table_header(["Start", "Size", "End"], [772, 892, 1002], 132)
        y = 160
        for hole in self.manager.holes[:8]:
            self.table_row([str(hole.start), str(hole.size), str(hole.end)], [772, 892, 1002], y)
            y += 28

        self.label("Segment tables", 772, 394, self.bold)
        self.table_header(["Process", "Segment", "Base", "Limit"], [772, 870, 982, 1084], 428)
        y = 456
        rows = self.manager.all_segments()
        if not rows:
            self.label("Allocate a process to show its segment table.", 772, y + 8, self.font, MUTED)
        for segment in rows[:9]:
            self.table_row(
                [
                    segment.process_name,
                    segment.segment_name,
                    str(segment.start),
                    str(segment.size),
                ],
                [772, 870, 982, 1084],
                y,
            )
            y += 28

    def block_color(self, block) -> tuple[int, int, int]:
        if block.kind == "hole":
            return (222, 245, 235)
        if block.kind == "reserved":
            return RESERVED
        process = block.label.split(":", 1)[0]
        return color_for_process(process)

    def panel(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=8)
        pygame.draw.rect(self.screen, LINE, rect, width=1, border_radius=8)

    def label(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font | None = None,
        color: tuple[int, int, int] = INK,
    ) -> None:
        self.screen.blit((font or self.font).render(text, True, color), (x, y))

    def row_text(self, left: str, right: str, x: int, y: int) -> None:
        self.label(left, x, y, self.small, INK)
        self.label(right, x + 160, y, self.small, MUTED)

    def table_header(self, headers: list[str], xs: list[int], y: int) -> None:
        pygame.draw.line(self.screen, LINE, (xs[0], y + 22), (1190, y + 22), 1)
        for header, x in zip(headers, xs):
            self.label(header, x, y, self.small, MUTED)

    def table_row(self, values: list[str], xs: list[int], y: int) -> None:
        pygame.draw.line(self.screen, (232, 235, 240), (xs[0], y + 24), (1190, y + 24), 1)
        for value, x in zip(values, xs):
            self.label(value, x, y, self.font, INK)

    def status_box(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (250, 251, 253), rect, border_radius=5)
        message = self.status
        if len(message) > 54:
            message = message[:51] + "..."
        self.label(message, rect.x + 8, rect.y + 3, self.small, self.status_color)

    def method_label(self) -> str:
        return "First-Fit" if self.method == "first_fit" else "Best-Fit"

    def status_ok(self, message: str) -> None:
        self.status = message
        self.status_color = GREEN

    def status_error(self, message: str) -> None:
        self.status = message
        self.status_color = RED


if __name__ == "__main__":
    try:
        MemoryAllocationApp().run()
    except pygame.error as exc:
        print(f"Pygame error: {exc}", file=sys.stderr)
        print(f"Run this project from: {Path(__file__).resolve().parent}", file=sys.stderr)
        raise
