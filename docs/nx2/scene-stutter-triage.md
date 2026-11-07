# Scene-transition stutter triage (Frizti v3)

This opt-in trace distinguishes long guest frame gaps, delayed host presentation,
shader translation, pipeline-build waits, and synchronous CPU readbacks. It does
not change the emulation, shader output, or frame pacing when disabled.

## Capture

Build a version containing this change, then add the following line to the
`nx2_switches.txt` next to `lichii.exe` (or `%APPDATA%\eden\nx2_switches.txt`):

```ini
EDEN_NX2_STUTTER_TRACE=1
```

Run the same screen/area transition twice, first on entry and then on return.
Keep shader caches, game settings, and save data unchanged. Close the emulator
before editing the switch file; it is read on process startup. For an optional
second run, use `EDEN_NX2_PRELOAD_ALL_PIPELINES=1` to test whether late cache
prebuilds are involved. This may consume several gigabytes of VRAM and lengthen
startup, especially with a very large cache. Do not enable it by default.

`EDEN_NX2_PERF_ON=async_pipelines` is a separate, existing experiment that moves
SPIR-V emission to workers; it does **not** move guest-to-IR translation off the
GPU emulation thread. Test it only in a separate A/B run after saving the baseline
log, and restore the switch if graphics become incorrect. It is not a default fix.

After gameplay, run:

```sh
python tools/nx2/scene_stutter_report.py path/to/eden_log.txt --min-ms 50
```

The reporter also recognizes v3's existing `Graphics/Compute pipeline built on
the GPU thread` lines, even from builds without the new trace.

## How to read the results

| Log label | Measurement |
|---|---|
| `guest present` | Time between successive guest presentation calls; includes intentional game loading |
| `host present` | Time between consecutive displayed frames, if Vulkan present-wait is supported |
| `shader translation` | CPU time for control-flow analysis, guest-to-IR translation, and dual-vertex merge on a single pipeline stage |
| `pipeline wait` | Elapsed wait for a graphics pipeline worker to finish at a dependent draw |
| `CPU readback` | CPU time spent requesting, submitting, and waiting for a GPU-written-memory download |

The report places events near each long present interval. This is *correlation*,
not proof of causation: events may overlap, and their durations must not be
added as if they were sequential. A long guest gap with no matching GPU event
could come from the game's own loading work or another emulator subsystem.

For a second, separately measured run, `EDEN_NX2_GPU_PROFILE=1` reports GPU
front/back thread zones and `EDEN_DKB_FRAME_TRACE=1` adds per-present timing.
GPU profiling has measurable overhead on some systems, so do not use that run
to compare raw frame times against a run without profiling. Do not change
reactive flushing or preflush switches just to make the reported wait disappear:
they protect data coherence and may affect image correctness.

To test the parser without a build or game files:

```sh
python -m unittest discover -s tools/nx2 -p test_scene_stutter_report.py -v
```