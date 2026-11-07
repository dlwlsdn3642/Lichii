#!/usr/bin/env python3
"""Tests for the scene-stutter log correlator (no emulator required)."""

import unittest

from scene_stutter_report import Event, parse_line, related_events, render


class SceneStutterReportTests(unittest.TestCase):
    def test_guest_present(self):
        event = parse_line(
            "[12.500123] Service <Info> Scene stutter guest present: "
            "frame=300 gap_ms=180.00 fence_ms=1.50 composite_ms=2.00 pace_ms=0.00"
        )
        self.assertEqual(event, Event(12.500123, "guest", 180, "300"))

    def test_shader_and_wait(self):
        shader = parse_line(
            "[12.450] Render.Vulkan <Info> Scene stutter shader translation: "
            "pipeline=abc0 stage=5 shader=def1 time_ms=85.30"
        )
        self.assertEqual(shader.kind, "shader")
        self.assertEqual(shader.duration_ms, 85.3)
        self.assertIn("shader=def1", shader.detail)
        waiting = parse_line(
            "[12.490] Render.Vulkan <Info> Scene stutter pipeline wait: "
            "pipeline=abc0 time_ms=22.50"
        )
        self.assertEqual(waiting.kind, "pipeline_wait")

    def test_old_v3_runtime_log(self):
        event = parse_line(
            "[28.500] Render.Vulkan <Info> Graphics pipeline built on the GPU thread "
            "in 310.5 ms: pipeline=0a12 s1:cd34"
        )
        self.assertEqual(event, Event(28.5, "runtime_pipeline", 310.5, "pipeline=0a12"))

    def test_host_and_cpu_readback(self):
        host = parse_line(
            "[13.300] Render.Vulkan <Info> Scene stutter host present: "
            "id=90 gap_ms=125.00 skipped_ids=2"
        )
        self.assertEqual(host, Event(13.3, "host", 125, "90"))
        readback = parse_line(
            "[13.100] HW.GPU <Info> Scene stutter CPU readback: "
            "address=0x1234 size=4096 time_ms=55.00"
        )
        self.assertEqual(readback, Event(13.1, "cpu_readback", 55, "address=0x1234"))

    def test_gap_correlates_prior_work_not_later_work(self):
        guest = Event(20.0, "guest", 200, "30")
        work = Event(19.9, "shader", 120, "pipeline=abc")
        old = Event(19.0, "shader", 200, "pipeline=old")
        late = Event(20.5, "pipeline_wait", 60, "pipeline=new")
        self.assertEqual(related_events([work, old, late], guest), [work])
        result = render([guest, work], min_ms=50, limit=10)
        self.assertIn("guest frame=30: 200.0 ms", result)
        self.assertIn("pipeline=abc", result)

    def test_no_events(self):
        self.assertIn("No scene-stutter events", render([], min_ms=50, limit=10))


if __name__ == "__main__":
    unittest.main()