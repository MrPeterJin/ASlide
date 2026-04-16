from __future__ import annotations

import pytest


def test_czi_slide_uses_injected_brightfield_adapter() -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    slide = CziSlide("demo.czi", adapter=adapter)

    assert slide.slide_family == "brightfield"
    assert slide.classify_slide_family() == "brightfield"
    assert slide.read_region((1, 2), 0, (3, 4)) == ((1, 2), 0, (3, 4))
    assert slide.get_thumbnail((64, 64)) == ("thumbnail", (64, 64))


def test_czi_slide_uses_injected_multiplex_adapter() -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 4,
            "pixel_type": "uint16",
            "channel_names": ("DAPI", "CD3"),
            "fluorophore_names": ("DAPI", "CD3"),
            "illumination_types": ("Epifluorescence", "Epifluorescence"),
            "excitation_wavelengths": (405.0, 488.0),
            "emission_wavelengths": (450.0, 520.0),
            "physical_pixel_sizes": (0.25, 0.25),
        }
    )

    slide = CziSlide("demo.czi", adapter=adapter)

    assert slide.slide_family == "multiplex"
    assert slide.classify_slide_family() == "multiplex"
    assert slide.list_biomarkers() == ["DAPI", "CD3"]
    assert slide.get_default_display_biomarker() == "DAPI"
    assert slide.properties["pixel_type"] == "uint16"
    assert slide.properties["channel_names"] == ("DAPI", "CD3")
    assert slide.properties["fluorophore_names"] == ("DAPI", "CD3")
    assert slide.properties["illumination_types"] == (
        "Epifluorescence",
        "Epifluorescence",
    )
    assert slide.properties["excitation_wavelengths"] == (405.0, 488.0)
    assert slide.properties["emission_wavelengths"] == (450.0, 520.0)
    assert slide.properties["physical_pixel_sizes"] == (0.25, 0.25)
    assert slide.read_biomarker_region((1, 2), 0, (3, 4), "DAPI") == (
        (1, 2),
        0,
        (3, 4),
        "DAPI",
    )


def test_czi_slide_fails_cleanly_without_adapter_dependency(monkeypatch) -> None:
    from Aslide.czi.czi_slide import CziSlide

    def _raise(_cls, _path):
        raise ImportError("Bio-Formats unavailable")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )

    with pytest.raises(ImportError, match="adapter|dependency|CZI"):
        CziSlide("demo.czi")


def test_czi_slide_builds_default_adapter_from_dependency(monkeypatch) -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(lambda cls, path: adapter),
    )

    slide = CziSlide("demo.czi")

    assert slide.classify_slide_family() == "brightfield"


def test_czi_slide_default_adapter_failure_has_clean_message(monkeypatch) -> None:
    from Aslide.czi.czi_slide import CziSlide

    def _raise(_cls, _path):
        raise ImportError("Bio-Formats unavailable")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )

    with pytest.raises(ImportError, match="Bio-Formats|CZI"):
        CziSlide("demo.czi")


def test_czi_slide_propagates_runtime_init_errors_from_bioformats(monkeypatch) -> None:
    from Aslide.czi.czi_slide import CziSlide

    def _raise(_cls, _path):
        raise RuntimeError("Negative position")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )

    with pytest.raises(RuntimeError, match="Negative position"):
        CziSlide("MAKYGIW_rescan.czi")


def test_czi_slide_exposes_shared_slide_metadata_from_adapter() -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    slide = CziSlide("demo.czi", adapter=adapter)

    assert slide.dimensions == (0, 0)
    assert slide.level_count == 1
    assert slide.level_dimensions == ((0, 0),)
    assert slide.level_downsamples == (1.0,)
    assert isinstance(slide.properties, dict)
    assert slide.properties["pixel_type"] == "bgr24"
    assert slide.get_best_level_for_downsample(2.0) == 0


def test_czi_slide_close_delegates_to_adapter_when_available() -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    slide = CziSlide("demo.czi", adapter=adapter)

    slide.close()


def test_extract_normalized_metadata_uses_raw_ome_xml_channel_fields() -> None:
    from Aslide.czi.adapter import _extract_normalized_metadata

    class FakeOme:
        image_count = 0

    ome_xml = """
    <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">
      <Image ID="Image:0" Name="sample">
        <Pixels DimensionOrder="XYCZT" SizeC="5" SizeX="10" SizeY="20" SizeZ="1" SizeT="1" Type="uint16">
          <Channel ID="Channel:0:0" Name="DAPI" Fluor="DAPI" IlluminationType="Epifluorescence" ExcitationWavelength="353.0" EmissionWavelength="465.0" />
          <Channel ID="Channel:0:1" Name="FITC" Fluor="FITC" IlluminationType="Epifluorescence" ExcitationWavelength="495.0" EmissionWavelength="519.0" />
        </Pixels>
      </Image>
    </OME>
    """

    extracted = _extract_normalized_metadata(FakeOme(), ome_xml)

    assert extracted["channel_count"] == 5
    assert extracted["pixel_type"] == "uint16"
    assert extracted["channel_names"] == ("DAPI", "FITC")
    assert extracted["fluorophore_names"] == ("DAPI", "FITC")
    assert extracted["illumination_types"] == ("Epifluorescence", "Epifluorescence")
    assert extracted["excitation_wavelengths"] == (353.0, 495.0)
    assert extracted["emission_wavelengths"] == (465.0, 519.0)


def test_extract_normalized_metadata_projects_physical_pixel_sizes_from_ome_xml() -> (
    None
):
    from Aslide.czi.adapter import CziAdapter, _extract_normalized_metadata
    from Aslide.czi.czi_slide import CziSlide

    class FakePixels:
        SizeC = 1
        PixelType = "uint16"

    class FakeImage:
        Pixels = FakePixels()

    class FakeOme:
        image_count = 1

        def image(self, _index: int) -> FakeImage:
            return FakeImage()

    ome_xml = """
    <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">
      <Image ID="Image:0" Name="sample">
        <Pixels DimensionOrder="XYCZT" SizeC="1" SizeX="10" SizeY="20" SizeZ="1" SizeT="1" Type="uint16" PhysicalSizeX="0.25" PhysicalSizeY="0.5">
          <Channel ID="Channel:0:0" Name="DAPI" Fluor="DAPI" IlluminationType="Epifluorescence" />
        </Pixels>
      </Image>
    </OME>
    """

    extracted = _extract_normalized_metadata(FakeOme(), ome_xml)
    adapter = CziAdapter.from_metadata(extracted)
    slide = CziSlide("demo.czi", adapter=adapter)

    assert extracted["physical_pixel_sizes"] == (0.25, 0.5)
    assert slide.properties["physical_pixel_sizes"] == (0.25, 0.5)


def test_czi_adapter_close_does_not_teardown_shared_jvm_between_opens(
    monkeypatch,
) -> None:
    from Aslide.czi.adapter import CziAdapter

    class FakeReader:
        def close(self) -> None:
            pass

    class FakeJavabridge:
        def __init__(self) -> None:
            self.env = None
            self.start_calls = 0
            self.kill_calls = 0
            self.restarted = False

        def get_env(self):
            return self.env

        def start_vm(self, class_path):
            _ = class_path
            if self.restarted:
                raise RuntimeError("cannot recreate JVM after close")
            self.start_calls += 1
            self.env = object()

        def kill_vm(self):
            self.kill_calls += 1
            self.env = None
            self.restarted = True

    class FakePixels:
        SizeC = 1
        PixelType = "uint16"

    class FakeImage:
        Pixels = FakePixels()

    class FakeOme:
        image_count = 1

        def image(self, _index: int) -> FakeImage:
            return FakeImage()

    fake_javabridge = FakeJavabridge()

    class FakeBioformats:
        JARS = ("fake.jar",)

        @staticmethod
        def get_omexml_metadata(path: str) -> str:
            _ = path
            return """
            <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">
              <Image ID="Image:0">
                <Pixels DimensionOrder="XYCZT" SizeC="1" SizeX="10" SizeY="20" SizeZ="1" SizeT="1" Type="uint16" />
              </Image>
            </OME>
            """

        @staticmethod
        def OMEXML(_metadata: str) -> FakeOme:
            return FakeOme()

        class ImageReader:
            def __init__(self, path: str) -> None:
                _ = path

            def read(self, **kwargs):
                _ = kwargs
                return [[0]]

    monkeypatch.setitem(__import__("sys").modules, "bioformats", FakeBioformats())
    monkeypatch.setitem(__import__("sys").modules, "javabridge", fake_javabridge)

    first = CziAdapter.from_bioformats("first.czi")
    first.close()

    assert fake_javabridge.kill_calls == 0

    second = CziAdapter.from_bioformats("second.czi")
    assert second._reader is not None


def test_czi_adapter_reuses_metadata_extraction_for_same_path(monkeypatch) -> None:
    from Aslide.czi.adapter import CziAdapter

    metadata_calls: list[str] = []

    class FakeReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeJavabridge:
        def get_env(self):
            return object()

        def start_vm(self, class_path):
            _ = class_path

        def kill_vm(self):
            pass

    class FakePixels:
        SizeC = 1
        SizeX = 10
        SizeY = 20
        PixelType = "uint16"

    class FakeImage:
        Pixels = FakePixels()

    class FakeOme:
        image_count = 1

        def image(self, _index: int) -> FakeImage:
            return FakeImage()

    class FakeBioformats:
        JARS = ("fake.jar",)

        @staticmethod
        def get_omexml_metadata(path: str) -> str:
            metadata_calls.append(path)
            return '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"><Image ID="Image:0"><Pixels DimensionOrder="XYCZT" SizeC="1" SizeX="10" SizeY="20" SizeZ="1" SizeT="1" Type="uint16" /></Image></OME>'

        @staticmethod
        def OMEXML(_metadata: str) -> FakeOme:
            return FakeOme()

        class ImageReader:
            def __init__(self, path: str) -> None:
                self._reader = FakeReader(path)

            def close(self) -> None:
                self._reader.close()

            def read(self, **kwargs):
                _ = kwargs
                return [[0]]

    fake_javabridge = FakeJavabridge()
    monkeypatch.setitem(__import__("sys").modules, "bioformats", FakeBioformats())
    monkeypatch.setitem(__import__("sys").modules, "javabridge", fake_javabridge)

    first = CziAdapter.from_bioformats("same.czi")
    second = CziAdapter.from_bioformats("same.czi")

    assert metadata_calls == ["same.czi"]
    assert first is not second
    assert first._reader is not second._reader
