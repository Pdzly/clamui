"""Tests for AppStream metadata validation."""

import xml.etree.ElementTree as ET
from pathlib import Path


def test_metainfo_xml_wellformed():
    """Test that metainfo.xml is well-formed XML."""
    metainfo_path = Path("com.github.rooki.clamui.metainfo.xml")
    assert metainfo_path.exists(), "Metainfo file should exist"

    # This will raise an exception if XML is malformed
    tree = ET.parse(metainfo_path)
    root = tree.getroot()

    assert root.tag == "component", "Root element should be 'component'"
    assert root.attrib.get("type") == "desktop-application", (
        "Component type should be desktop-application"
    )


def test_metainfo_required_elements():
    """Test that all required AppStream elements are present."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    # Required elements per AppStream spec
    required_elements = [
        "id",
        "name",
        "summary",
        "metadata_license",
        "project_license",
        "description",
    ]

    for element in required_elements:
        found = root.find(element)
        assert found is not None, f"Required element '{element}' should be present"
        assert found.text or len(found), f"Element '{element}' should have content"


def test_metainfo_app_id():
    """Test that app ID matches expected format."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    app_id = root.find("id")
    assert app_id is not None
    assert app_id.text == "com.github.rooki.clamui", "App ID should match reverse-DNS format"


def test_metainfo_launchable():
    """Test that launchable element references correct desktop file."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    launchable = root.find("launchable")
    assert launchable is not None, "Launchable element should be present"
    assert launchable.attrib.get("type") == "desktop-id", "Launchable type should be desktop-id"
    assert launchable.text == "com.github.rooki.clamui.desktop", (
        "Should reference correct desktop file"
    )


def test_metainfo_screenshots():
    """Test that screenshots section exists."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    screenshots = root.find("screenshots")
    assert screenshots is not None, "Screenshots section should be present"

    screenshot_list = screenshots.findall("screenshot")
    assert len(screenshot_list) >= 1, "At least one screenshot should be defined"

    default_screenshot = screenshots.find("screenshot[@type='default']")
    assert default_screenshot is not None, "Default screenshot should be defined"


def test_metainfo_releases():
    """Test that releases section exists with at least one release."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    releases = root.find("releases")
    assert releases is not None, "Releases section should be present"

    release_list = releases.findall("release")
    assert len(release_list) >= 1, "At least one release should be defined"

    latest_release = release_list[0]
    assert "version" in latest_release.attrib, "Release should have version"
    assert "date" in latest_release.attrib, "Release should have date"


def test_metainfo_content_rating():
    """Test that content rating is present (required for Flathub)."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    content_rating = root.find("content_rating")
    assert content_rating is not None, "Content rating should be present"
    assert content_rating.attrib.get("type") == "oars-1.1", "Content rating should use OARS 1.1"


def test_metainfo_provides_binary():
    """Test that provides section includes the binary."""
    tree = ET.parse("com.github.rooki.clamui.metainfo.xml")
    root = tree.getroot()

    provides = root.find("provides")
    assert provides is not None, "Provides section should be present"

    binary = provides.find("binary")
    assert binary is not None, "Binary element should be present"
    assert binary.text == "clamui", "Binary should be 'clamui'"
