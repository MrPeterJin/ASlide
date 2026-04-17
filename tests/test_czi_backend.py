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
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    def _raise(_cls, _path):
        raise ImportError("Bio-Formats unavailable")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )
    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_czifile",
        classmethod(lambda cls, path: adapter),
    )

    slide = CziSlide("demo.czi")

    assert slide.classify_slide_family() == "brightfield"


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

    def _raise(_cls, _path):
        raise ImportError("Bio-Formats unavailable")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )
    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_czifile",
        classmethod(lambda cls, path: adapter),
    )

    slide = CziSlide("demo.czi")

    assert slide.classify_slide_family() == "multiplex"


def test_czi_slide_falls_back_on_runtime_init_errors_from_bioformats(
    monkeypatch,
) -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    def _raise(_cls, _path):
        raise RuntimeError("Negative position")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_czifile",
        classmethod(lambda cls, path: adapter),
    )

    slide = CziSlide("MAKYGIW_rescan.czi")

    assert slide.classify_slide_family() == "brightfield"


def test_czi_slide_falls_back_to_czifile_when_bioformats_init_fails(
    monkeypatch,
) -> None:
    from Aslide.czi.adapter import CziAdapter
    from Aslide.czi.czi_slide import CziSlide

    adapter = CziAdapter.from_metadata(
        {
            "channel_count": 3,
            "illumination_types": ("Transmitted",),
            "pixel_type": "bgr24",
        }
    )

    def _raise(_cls, _path):
        raise RuntimeError("Bio-Formats init failed")

    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_bioformats",
        classmethod(_raise),
    )
    monkeypatch.setattr(
        "Aslide.czi.adapter.CziAdapter.from_czifile",
        classmethod(lambda cls, path: adapter),
    )

    slide = CziSlide("demo.czi")

    assert slide.classify_slide_family() == "brightfield"


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


def test_from_czifile_classifies_multiplex_from_czi_xml(monkeypatch) -> None:
    from Aslide.czi.adapter import CziAdapter

    class FakeSubBlock:
        def __init__(self, *, m_index: int) -> None:
            self.m_index = m_index

    class FakeCziFile:
        def __init__(self, path: str) -> None:
            self.path = path
            self.subblocks = [FakeSubBlock(m_index=0)]

        def close(self) -> None:
            pass

    def fake_czifile_open(path: str):
        return FakeCziFile(path)

    monkeypatch.setattr("Aslide.czi.adapter.czifile.CziFile", fake_czifile_open)
    monkeypatch.setattr(
        "Aslide.czi.adapter._extract_czi_xml",
        lambda _czi: (
            "<OME xmlns='http://www.openmicroscopy.org/Schemas/OME/2016-06'>"
            "<Image ID='Image:0'><Pixels SizeC='2' SizeX='8' SizeY='4' Type='uint16'>"
            "<Channel ID='Channel:0:0' Name='DAPI' Fluor='DAPI' />"
            "<Channel ID='Channel:0:1' Name='CD3' Fluor='CD3' />"
            "</Pixels></Image></OME>"
        ),
    )

    adapter = CziAdapter.from_czifile("multiplex.czi")

    assert adapter.classify_slide_family() == "multiplex"
    assert adapter.properties["channel_names"] == ("DAPI", "CD3")


def test_from_czifile_exposes_biomarker_names(monkeypatch) -> None:
    from Aslide.czi.adapter import CziAdapter

    class FakeSubBlock:
        def __init__(self, *, m_index: int) -> None:
            self.m_index = m_index

    class FakeCziFile:
        def __init__(self, path: str) -> None:
            self.path = path
            self.subblocks = [FakeSubBlock(m_index=0)]

        def close(self) -> None:
            pass

    monkeypatch.setattr("Aslide.czi.adapter.czifile.CziFile", FakeCziFile)
    monkeypatch.setattr(
        "Aslide.czi.adapter._extract_czi_xml",
        lambda _czi: (
            "<OME xmlns='http://www.openmicroscopy.org/Schemas/OME/2016-06'>"
            "<Image ID='Image:0'><Pixels SizeC='2' SizeX='8' SizeY='4' Type='uint16'>"
            "<Channel ID='Channel:0:0' Name='DAPI' Fluor='DAPI' />"
            "<Channel ID='Channel:0:1' Name='CD3' Fluor='CD3' />"
            "</Pixels></Image></OME>"
        ),
    )

    adapter = CziAdapter.from_czifile("multiplex.czi")

    assert adapter.list_biomarkers() == ["DAPI", "CD3"]
    assert adapter.get_default_display_biomarker() == "DAPI"


def test_from_czifile_reads_minimal_biomarker_region_from_subblocks(
    monkeypatch,
) -> None:
    from Aslide.czi.adapter import CziAdapter

    class FakeSubBlock:
        def __init__(
            self,
            *,
            m_index: int,
            data: list[list[int]],
            dimension_entries: tuple[tuple[str, int], ...],
        ) -> None:
            self.m_index = m_index
            self._data = data
            self.dimension_entries = dimension_entries
            self.dimension_starts = {name: start for name, start in dimension_entries}

    class FakeCziFile:
        def __init__(self, path: str) -> None:
            self.path = path
            self.subblocks = [
                FakeSubBlock(
                    m_index=0,
                    data=[
                        [100, 101, 102, 103, 104, 105, 106, 107],
                        [110, 111, 112, 113, 114, 115, 116, 117],
                        [120, 121, 122, 123, 124, 125, 126, 127],
                        [130, 131, 132, 133, 134, 135, 136, 137],
                        [140, 141, 142, 143, 144, 145, 146, 147],
                        [150, 151, 152, 153, 154, 155, 156, 157],
                        [160, 161, 162, 163, 164, 165, 166, 167],
                        [170, 171, 172, 173, 174, 175, 176, 177],
                    ],
                    dimension_entries=(("X", 10), ("Y", 20)),
                )
            ]

        def close(self) -> None:
            pass

    monkeypatch.setattr("Aslide.czi.adapter.czifile.CziFile", FakeCziFile)
    monkeypatch.setattr(
        "Aslide.czi.adapter._extract_czi_xml",
        lambda _czi: (
            "<OME xmlns='http://www.openmicroscopy.org/Schemas/OME/2016-06'>"
            "<Image ID='Image:0'><Pixels SizeC='1' SizeX='8' SizeY='8' Type='uint16'>"
            "<Channel ID='Channel:0:0' Name='DAPI' Fluor='DAPI' />"
            "</Pixels></Image></OME>"
        ),
    )

    adapter = CziAdapter.from_czifile("multiplex.czi")

    assert adapter.read_biomarker_region((12, 23), 0, (3, 2), "DAPI") == [
        [132, 133, 134],
        [142, 143, 144],
    ]


def test_from_bioformats_keeps_biomarker_region_on_reader_path(monkeypatch) -> None:
    from Aslide.czi.adapter import CziAdapter

    class FakeReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.calls: list[dict[str, object]] = []

        def read(self, **kwargs):
            self.calls.append(kwargs)
            return [[9, 8], [7, 6]]

        def close(self) -> None:
            pass

    class FakeJavabridge:
        def get_env(self):
            return object()

        def start_vm(self, class_path):
            _ = class_path

        def kill_vm(self):
            pass

    class FakePixels:
        SizeC = 1
        SizeX = 2
        SizeY = 2
        PixelType = "uint16"

    class FakeImage:
        Pixels = FakePixels()

    class FakeOme:
        image_count = 1

        def image(self, _index: int) -> FakeImage:
            return FakeImage()

    fake_reader = FakeReader("bioformats.czi")

    class FakeBioformats:
        JARS = ("fake.jar",)

        @staticmethod
        def get_omexml_metadata(path: str) -> str:
            _ = path
            return (
                '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">'
                '<Image ID="Image:0"><Pixels DimensionOrder="XYCZT" SizeC="1" SizeX="2" SizeY="2" '
                'SizeZ="1" SizeT="1" Type="uint16">'
                '<Channel ID="Channel:0:0" Name="DAPI" Fluor="DAPI" '
                'IlluminationType="Epifluorescence" /></Pixels></Image></OME>'
            )

        @staticmethod
        def OMEXML(_metadata: str) -> FakeOme:
            return FakeOme()

        class ImageReader:
            def __init__(self, path: str) -> None:
                _ = path
                self._reader = fake_reader

            def read(self, **kwargs):
                return self._reader.read(**kwargs)

            def close(self) -> None:
                self._reader.close()

    monkeypatch.setitem(__import__("sys").modules, "bioformats", FakeBioformats())
    monkeypatch.setitem(__import__("sys").modules, "javabridge", FakeJavabridge())

    adapter = CziAdapter.from_bioformats("bioformats.czi")

    assert adapter.read_biomarker_region((0, 0), 0, (2, 2), "DAPI") == [[9, 8], [7, 6]]
    assert fake_reader.calls, "expected the Bio-Formats reader path to be used"


def test_from_czifile_parses_zeiss_image_document_metadata(monkeypatch) -> None:
    from Aslide.czi.adapter import CziAdapter

    class FakeCziFile:
        def __init__(self, path: str) -> None:
            self.path = path
            self.axes = "ZCYX"
            self.shape = (2, 3, 5, 7)
            self.subblocks = []

        def close(self) -> None:
            pass

    monkeypatch.setattr("Aslide.czi.adapter.czifile.CziFile", FakeCziFile)
    monkeypatch.setattr(
        "Aslide.czi.adapter._extract_czi_xml",
        lambda _czi: (
            "<ImageDocument>"
            "<Metadata>"
            "<Scaling>"
            "<Items>"
            "<Distance Id='X'><Value>0.25</Value></Distance>"
            "<Distance Id='Y'><Value>0.5</Value></Distance>"
            "</Items>"
            "</Scaling>"
            "</Metadata>"
            "</ImageDocument>"
        ),
    )

    adapter = CziAdapter.from_czifile("multiplex.czi")

    assert adapter.classify_slide_family() == "multiplex"
    assert adapter.dimensions == (7, 5)
    assert adapter.properties["physical_pixel_sizes"] == (0.25, 0.5)
