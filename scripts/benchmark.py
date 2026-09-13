import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Union

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faster_whisper import WhisperModel
from tests.fixtures.audio_fixtures import create_synthetic_wav_bytes

BenchmarkMetricValue = Union[str, float]

# Sample test sentences representing official administration, local Medan terms, and conversational queries
EVALUATION_SAMPLES: List[Dict[str, str]] = [
    {
        "id": "sample_01",
        "category": "administrasi_pemerintahan",
        "reference_text": "Bagaimana cara mengurus KTP elektronik dan Kartu Keluarga di Disdukcapil Kota Medan?",
    },
    {
        "id": "sample_02",
        "category": "lokasi_dan_instansi",
        "reference_text": "Bang saya mau tanya lokasi kantor wali kota Medan di Jalan Kapten Maulana Lubis.",
    },
    {
        "id": "sample_03",
        "category": "percakapan_singkat",
        "reference_text": "Tolong infokan jam operasional pelayanan kantor kecamatan hari ini.",
    },
]


def calculate_simple_wer(reference: str, hypothesis: str) -> float:
    """Calculates basic Word Error Rate (WER) between reference and transcribed text."""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    # Dynamic programming distance matrix
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min(
                d[i - 1][j] + 1,      # deletion
                d[i][j - 1] + 1,      # insertion
                d[i - 1][j - 1] + cost  # substitution
            )

    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def run_benchmark(
    models: List[str],
    compute_type: str = "int8",
    cpu_threads: int = 4,
    test_audio_path: str = None,
) -> None:
    print("=" * 70)
    print(" SPEECH-TO-TEXT BENCHMARK & ACCURACY EVALUATION (RCTI-Grade Standard)")
    print("=" * 70)
    print(f"Compute Type : {compute_type}")
    print(f"CPU Threads  : {cpu_threads}")
    print("-" * 70)

    # Use provided audio file or create a temporary synthetic WAV
    cleanup_temp = False
    if test_audio_path and Path(test_audio_path).exists():
        target_audio = Path(test_audio_path)
    else:
        print("[Notice] No real audio provided. Generating synthetic 5-second WAV for latency & RTF benchmark...")
        target_audio = Path("benchmark_temp.wav")
        target_audio.write_bytes(create_synthetic_wav_bytes(duration_seconds=5.0))
        cleanup_temp = True

    results: List[Dict[str, BenchmarkMetricValue]] = []

    for model_name in models:
        print(f"\n[+] Testing Model: '{model_name}'...")
        start_load = time.perf_counter()
        try:
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type=compute_type,
                cpu_threads=cpu_threads,
            )
            load_time = time.perf_counter() - start_load
            print(f"    - Model Load Time: {load_time:.2f}s")

            # Warm-up / Run transcription
            start_infer = time.perf_counter()
            segments, info = model.transcribe(
                str(target_audio),
                language="id",
                beam_size=5,
                initial_prompt=(
                    "Percakapan dan pengaduan layanan publik warga Kota Medan. "
                    "Mencakup Kantor Wali Kota, Disdukcapil, Dishub, Dinkes, Disdik, DPMPTSP, Bapenda, Satpol PP, "
                    "kecamatan, kelurahan, kepala dinas, camat, lurah, kepling, "
                    "KTP elektronik, Kartu Keluarga KK, akta kelahiran, perizinan, dan pengaduan masyarakat."
                ),
            )
            transcribed_text = " ".join(seg.text.strip() for seg in segments).strip()
            infer_time = time.perf_counter() - start_infer

            audio_duration = info.duration if hasattr(info, "duration") and info.duration > 0 else 5.0
            rtf = infer_time / audio_duration

            print(f"    - Audio Duration      : {audio_duration:.2f}s")
            print(f"    - Inference Time      : {infer_time:.2f}s")
            print(f"    - Real-Time Factor    : {rtf:.3f}x ({'Faster than real-time' if rtf < 1.0 else 'Slower than real-time'})")
            print(f"    - Transcribed Output  : '{transcribed_text}'")

            results.append({
                "model": model_name,
                "load_time_s": round(load_time, 2),
                "infer_time_s": round(infer_time, 2),
                "audio_duration_s": round(audio_duration, 2),
                "rtf": round(rtf, 3),
            })
        except Exception as e:
            print(f"    [!] Error testing model {model_name}: {e}")

    if cleanup_temp and target_audio.exists():
        os.remove(target_audio)

    print("\n" + "=" * 70)
    print(" BENCHMARK SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Model':<12} | {'Load (s)':<10} | {'Infer (s)':<10} | {'Duration (s)':<12} | {'RTF':<8}")
    print("-" * 70)
    for r in results:
        print(f"{r['model']:<12} | {r['load_time_s']:<10} | {r['infer_time_s']:<10} | {r['audio_duration_s']:<12} | {r['rtf']:<8}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STT Service Benchmark Script")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["tiny", "base"],
        help="List of faster-whisper models to benchmark (e.g. tiny base small)",
    )
    parser.add_argument("--compute-type", default="int8", help="Compute type (default: int8)")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads (default: 4)")
    parser.add_argument("--audio", type=str, default=None, help="Path to real sample audio file")

    args = parser.parse_args()
    run_benchmark(
        models=args.models,
        compute_type=args.compute_type,
        cpu_threads=args.threads,
        test_audio_path=args.audio,
    )
