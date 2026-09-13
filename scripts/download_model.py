import argparse
import shutil
import sys
from pathlib import Path
from typing import List

REQUIRED_MODEL_FILES: List[str] = [
    "model.bin",
    "config.json",
    "tokenizer.json",
    "vocabulary.txt",
]


def copy_from_hf_cache(model_name: str, target_dir: Path) -> bool:
    """Attempts to copy model weights from existing local Hugging Face cache."""
    cache_hub = Path.home() / ".cache" / "huggingface" / "hub"
    model_cache_name = f"models--Systran--faster-whisper-{model_name}"
    model_cache_path = cache_hub / model_cache_name

    if not model_cache_path.exists():
        return False

    snapshots = list(model_cache_path.glob("snapshots/*"))
    if not snapshots:
        return False

    latest_snapshot = snapshots[0]
    print(f"[+] Found cached weights at: {latest_snapshot}")
    target_dir.mkdir(parents=True, exist_ok=True)

    for file_name in REQUIRED_MODEL_FILES:
        src = latest_snapshot / file_name
        dst = target_dir / file_name
        if src.exists():
            print(f"    - Copying {file_name} ({src.stat().st_size // 1024} KB)...")
            shutil.copy2(src, dst)
        else:
            print(f"    [!] Warning: Missing expected file {file_name} in snapshot")

    return True


def download_from_hub(model_name: str, target_dir: Path) -> None:
    """Downloads model weights directly from Hugging Face Hub using faster_whisper helper."""
    from faster_whisper import download_model

    print(f"[+] Downloading '{model_name}' from Hugging Face Hub...")
    downloaded_path = download_model(model_name, output_dir=str(target_dir))
    print(f"[+] Successfully downloaded model to: {downloaded_path}")


def verify_target_model(target_dir: Path) -> bool:
    """Verifies all required model files exist and are non-empty in the destination."""
    missing_or_empty: List[str] = []
    for file_name in REQUIRED_MODEL_FILES:
        p = target_dir / file_name
        if not p.exists() or p.stat().st_size == 0:
            missing_or_empty.append(file_name)

    if missing_or_empty:
        print(f"[!] Verification failed. Missing or empty files: {missing_or_empty}")
        return False

    total_size_mb = sum(p.stat().st_size for p in target_dir.glob("*")) / (1024 * 1024)
    print(f"[OK] Model verified successfully in '{target_dir}' (Total size: {total_size_mb:.2f} MB)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Download or extract faster-whisper model weights locally.")
    parser.add_argument(
        "--model",
        type=str,
        default="small",
        help="Model name (e.g. tiny, base, small, medium, large-v3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Destination directory (default: models/{model})",
    )

    args = parser.parse_args()
    model_name = args.model
    output_dir = Path(args.output) if args.output else Path("models") / model_name

    print("=" * 70)
    print(f" FASTER-WHISPER OFFLINE MODEL SETUP: '{model_name}'")
    print(f" Target Directory: {output_dir.resolve()}")
    print("=" * 70)

    # Check if already exists and valid
    if output_dir.exists() and verify_target_model(output_dir):
        print(f"[OK] Model '{model_name}' is already complete and verified. No action needed.")
        sys.exit(0)

    # 1. Try copying from local user cache first (instant, 0 internet)
    copied = copy_from_hf_cache(model_name=model_name, target_dir=output_dir)
    if not copied:
        print("[Notice] Model not found in local Hugging Face cache. Downloading from internet...")
        download_from_hub(model_name=model_name, target_dir=output_dir)

    # 2. Final verification
    if not verify_target_model(output_dir):
        print("[!] Model setup failed.")
        sys.exit(1)

    print("\n[OK] Offline model setup complete!")
    print(f"    You can now set STT_MODEL={output_dir.as_posix()} in your .env or docker-compose.yml")


if __name__ == "__main__":
    main()
