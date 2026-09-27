"""Normalize a setuptools source archive for reproducible release bundles."""

import argparse
import gzip
import tarfile
from pathlib import Path


def normalize(source: Path, destination: Path, epoch: int) -> None:
    """Rewrite a source tarball with stable ordering and ownership/timestamps."""

    with tarfile.open(source, "r:gz") as archive, destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as output:
                for member in sorted(archive.getmembers(), key=lambda item: item.name):
                    if not (member.isfile() or member.isdir()):
                        raise ValueError("source archive contains an unsupported file type")
                    normalized = tarfile.TarInfo(member.name)
                    normalized.type = tarfile.DIRTYPE if member.isdir() else tarfile.REGTYPE
                    normalized.mode = member.mode & 0o777
                    normalized.size = 0 if member.isdir() else member.size
                    normalized.mtime = epoch
                    normalized.uid = normalized.gid = 0
                    normalized.uname = normalized.gname = ""
                    payload = None if member.isdir() else archive.extractfile(member)
                    output.addfile(normalized, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--epoch", type=int, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        parser.error("source and destination must be different files")
    normalize(args.source, args.destination, args.epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
