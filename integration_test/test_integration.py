import tarfile
import typing

from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import pytest

from pycargoebuild.__main__ import main
from pycargoebuild.fetch import fetch_files_using_wget, verify_files


class Package(typing.NamedTuple):
    url: str
    checksum: str
    directories: typing.List[str]
    expected_filename: str


PACKAGES = {
    "cryptography-38.0.3.ebuild": Package(
        url="https://files.pythonhosted.org/packages/13/dd/"
            "a9608b7aebe5d2dc0c98a4b2090a6b815628efa46cc1c046b89d8cd25f4c/"
            "cryptography-38.0.3.tar.gz",
        checksum="bfbe6ee19615b07a98b1d2287d6a6073"
                 "f734735b49ee45b11324d85efc4d5cbd",
        directories=["cryptography-38.0.3/src/rust"],
        expected_filename="cryptography-rust-0.1.0.ebuild"),
    "watchfiles-0.18.1.ebuild": Package(
        url="https://files.pythonhosted.org/packages/5e/6a/"
            "2760278f309655cc7305392b0bb664738104202bf5d50396eb138258c5ca/"
            "watchfiles-0.18.1.tar.gz",
        checksum="4ec0134a5e31797eb3c6c624dbe9354f"
                 "2a8ee9c720e0b46fc5b7bab472b7c6d4",
        directories=["watchfiles-0.18.1"],
        expected_filename="watchfiles_rust_notify-0.18.1.ebuild"),
}


@pytest.mark.parametrize("ebuild", PACKAGES)
def test_integration(tmp_path, capfd, ebuild):
    pkg_info = PACKAGES[ebuild]

    test_dir = Path(__file__).parent
    dist_dir = test_dir / "dist"
    dist_dir.mkdir(exist_ok=True)
    archive_name = PurePosixPath(urlparse(pkg_info.url).path).name
    dist_file = dist_dir / archive_name

    fetch_files_using_wget([(pkg_info.url, dist_file)])
    verify_files([(dist_file, pkg_info.checksum)])
    with tarfile.open(dist_file, "r") as tarf:
        for directory in pkg_info.directories:
            for filename in ("Cargo.lock", "Cargo.toml"):
                member = tarf.getmember(f"{directory}/{filename}")
                assert member is not None
                tarf.extract(member, tmp_path, set_attrs=False)

    assert main(
        "test", "-d", str(dist_dir),
        "-o", str(tmp_path / "{name}-{version}.ebuild"),
        *(str(tmp_path / directory) for directory in pkg_info.directories)
        ) == 0
    stdout, _ = capfd.readouterr()
    assert stdout == str(tmp_path / pkg_info.expected_filename) + "\n"
    assert (
        (tmp_path / pkg_info.expected_filename).read_text(encoding="utf-8") ==
        (test_dir / ebuild).read_text(encoding="utf-8"))