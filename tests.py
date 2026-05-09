import unittest

from memory_allocator import AllocationError, Hole, MemoryManager


class MemoryManagerTests(unittest.TestCase):
    def test_default_memory_starts_with_no_holes(self):
        manager = MemoryManager()

        self.assertEqual(manager.holes, [])
        self.assertEqual([(b.start, b.size, b.kind) for b in manager.snapshot()], [(0, 1024, "reserved")])

    def test_first_fit_allocates_segments_and_updates_holes(self):
        manager = MemoryManager()
        manager.configure_memory(500, [Hole(0, 100), Hole(200, 200)])

        manager.allocate_process("P1", [("Code", 50), ("Data", 120)], "first_fit")

        self.assertEqual([(h.start, h.size) for h in manager.holes], [(50, 50), (320, 80)])
        self.assertEqual([(s.segment_name, s.start, s.size) for s in manager.all_segments()], [("Code", 0, 50), ("Data", 200, 120)])

    def test_best_fit_chooses_smallest_available_hole(self):
        manager = MemoryManager()
        manager.configure_memory(600, [Hole(0, 300), Hole(350, 80), Hole(450, 120)])

        manager.allocate_process("P1", [("Stack", 70)], "best_fit")

        self.assertEqual(manager.allocations["P1"][0].start, 350)
        self.assertEqual([(h.start, h.size) for h in manager.holes], [(0, 300), (420, 10), (450, 120)])

    def test_failed_process_rolls_back_all_segments(self):
        manager = MemoryManager()
        manager.configure_memory(200, [Hole(0, 80), Hole(120, 40)])

        with self.assertRaises(AllocationError):
            manager.allocate_process("P1", [("Code", 70), ("Data", 60)], "first_fit")

        self.assertEqual(manager.allocations, {})
        self.assertEqual([(h.start, h.size) for h in manager.holes], [(0, 80), (120, 40)])

    def test_deallocate_merges_neighboring_holes(self):
        manager = MemoryManager()
        manager.configure_memory(300, [Hole(0, 300)])
        manager.allocate_process("P1", [("A", 50)], "first_fit")
        manager.allocate_process("P2", [("A", 50)], "first_fit")
        manager.deallocate_process("P1")
        manager.deallocate_process("P2")

        self.assertEqual([(h.start, h.size) for h in manager.holes], [(0, 300)])


if __name__ == "__main__":
    unittest.main()
