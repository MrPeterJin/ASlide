from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from typing import Any, Iterable, cast
from xml.etree import ElementTree as ET

from PIL import Image

from .metadata import (
    NormalizedCziMetadata,
    classify_czi_family,
    normalize_czi_metadata,
)

try:
    import czifile as czifile  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    czifile = None


_BIOFORMATS_METADATA_CACHE: dict[str, tuple[dict[str, Any], tuple[int, int]]] = {}


@dataclass
class CziAdapter:
    metadata: NormalizedCziMetadata
    dimensions: tuple[int, int] = (0, 0)
    level_count: int = 1
    level_dimensions: tuple[tuple[int, int], ...] = ((0, 0),)
    level_downsamples: tuple[float, ...] = (1.0,)
    properties: dict[str, str] = field(default_factory=dict)
    _reader: Any | None = None
    _backend: str = "metadata"
    _javabridge: Any | None = None
    _owns_vm: bool = False

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "CziAdapter":
        normalized = normalize_czi_metadata(metadata)
        return cls(
            metadata=normalized,
            dimensions=(0, 0),
            level_count=1,
            level_dimensions=((0, 0),),
            level_downsamples=(1.0,),
            properties={
                "aslide.czi.adapter": "metadata",
                **_metadata_properties(normalized),
            },
        )

    @classmethod
    def from_bioformats(cls, path: str) -> "CziAdapter":
        try:
            bioformats = importlib.import_module("bioformats")
            javabridge = importlib.import_module("javabridge")
        except ImportError as exc:
            raise ImportError(
                "CZI support requires optional dependencies: python-bioformats and javabridge"
            ) from exc

        owns_vm = False
        if not javabridge.get_env():
            javabridge.start_vm(class_path=bioformats.JARS)
            owns_vm = True

        try:
            cached = _BIOFORMATS_METADATA_CACHE.get(path)
            if cached is None:
                ome_metadata = bioformats.get_omexml_metadata(path)
                ome = bioformats.OMEXML(ome_metadata)
                cached = (
                    _extract_normalized_metadata(ome, ome_metadata),
                    _extract_dimensions(ome),
                )
                _BIOFORMATS_METADATA_CACHE[path] = cached
            image_reader = bioformats.ImageReader(path)
        except Exception as exc:
            if owns_vm and javabridge.get_env():
                javabridge.kill_vm()
            raise RuntimeError(
                f"Failed to initialize Bio-Formats CZI adapter: {exc}"
            ) from exc

        normalized_raw, dimensions = cached
        normalized = normalize_czi_metadata(normalized_raw)
        return cls(
            metadata=normalized,
            dimensions=dimensions,
            level_count=1,
            level_dimensions=(dimensions,),
            level_downsamples=(1.0,),
            properties={
                "openslide.vendor": "Zeiss",
                "aslide.czi.backend": "bioformats",
                **_metadata_properties(normalized),
            },
            _reader=image_reader,
            _backend="bioformats",
            _javabridge=javabridge,
            _owns_vm=owns_vm,
        )

    @classmethod
    def from_czifile(cls, path: str) -> "CziAdapter":
        if czifile is None:
            raise ImportError("CZI support requires optional dependency: czifile")

        try:
            czi_file = czifile.CziFile(path)
            metadata, dimensions = _extract_czifile_metadata(czi_file)
            return cls(
                metadata=normalize_czi_metadata(metadata),
                dimensions=dimensions,
                level_count=1,
                level_dimensions=(dimensions,),
                level_downsamples=(1.0,),
                properties={
                    "openslide.vendor": "Zeiss",
                    "aslide.czi.backend": "czifile",
                    **_metadata_properties(normalize_czi_metadata(metadata)),
                },
                _reader=czi_file,
                _backend="czifile",
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize czifile CZI adapter: {exc}"
            ) from exc

    def classify_slide_family(self) -> str:
        return classify_czi_family(self.metadata)

    def list_biomarkers(self) -> list[str]:
        return [name for name in self.metadata.fluorophore_names if name]

    def get_default_display_biomarker(self) -> str:
        biomarkers = self.list_biomarkers()
        if not biomarkers:
            raise LookupError("missing default biomarker")
        return biomarkers[0]

    def read_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
    ) -> Image.Image | tuple[tuple[int, int], int, tuple[int, int]]:
        if self._backend == "bioformats" and self._reader is not None:
            if level != 0:
                raise ValueError(
                    "Bio-Formats CZI adapter currently supports only level 0"
                )
            x, y = location
            width, height = size
            image_data = self._reader.read(
                c=0,
                z=0,
                t=0,
                series=0,
                rescale=False,
                XYWH=(x, y, width, height),
            )
            if len(image_data.shape) == 2:
                return Image.fromarray(image_data, mode="L")
            return Image.fromarray(image_data)
        return (location, level, size)

    def get_thumbnail(
        self, size: tuple[int, int]
    ) -> Image.Image | tuple[str, tuple[int, int]]:
        if self._backend == "bioformats" and self._reader is not None:
            region = self.read_region((0, 0), 0, self.dimensions)
            if isinstance(region, Image.Image):
                return region.resize(size, Image.Resampling.LANCZOS)
        return ("thumbnail", size)

    def read_biomarker_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
        biomarker: str,
    ) -> Image.Image | tuple[tuple[int, int], int, tuple[int, int], str]:
        if biomarker not in self.list_biomarkers():
            raise LookupError(f"Unknown biomarker: {biomarker}")
        if self._backend == "bioformats" and self._reader is not None:
            if level != 0:
                raise ValueError("CZI adapter currently supports only level 0")
            channel_index = self.list_biomarkers().index(biomarker)
            return _read_bioformats_biomarker_region(
                self._reader, location, size, channel_index
            )
        if self._backend == "czifile" and self._reader is not None:
            if level != 0:
                raise ValueError("CZI adapter currently supports only level 0")
            channel_index = self.list_biomarkers().index(biomarker)
            return _read_czifile_biomarker_region(
                self._reader, location, size, channel_index
            )
        return (location, level, size, biomarker)

    def get_best_level_for_downsample(self, downsample: float) -> int:
        _ = downsample
        return 0

    def close(self) -> None:
        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass


def _extract_dimensions(ome: Any) -> tuple[int, int]:
    try:
        if ome.image_count <= 0:
            return (0, 0)
        pixels = ome.image(0).Pixels
        return (
            int(getattr(pixels, "SizeX", 0) or 0),
            int(getattr(pixels, "SizeY", 0) or 0),
        )
    except Exception:
        return (0, 0)


def _extract_normalized_metadata(
    ome: Any, ome_xml: str | None = None
) -> dict[str, Any]:
    channel_count = 0
    pixel_type = None
    illumination_types: list[str] = []
    fluorophore_names: list[str] = []
    excitation_wavelengths: list[float] = []
    emission_wavelengths: list[float] = []
    channel_names: list[str] = []
    physical_pixel_sizes: list[float] = []

    try:
        if ome.image_count > 0:
            pixels = ome.image(0).Pixels
            channel_count = int(getattr(pixels, "SizeC", 0) or 0)
            pixel_type = getattr(pixels, "PixelType", None)
            for index in range(channel_count):
                channel = pixels.Channel(index)
                name = getattr(channel, "Name", None)
                fluor = getattr(channel, "Fluor", None)
                excitation = getattr(channel, "ExcitationWavelength", None)
                emission = getattr(channel, "EmissionWavelength", None)
                if name:
                    channel_names.append(str(name))
                if fluor:
                    fluorophore_names.append(str(fluor))
                illumination = getattr(channel, "IlluminationType", None)
                if illumination:
                    illumination_types.append(str(illumination))
                if excitation is not None:
                    excitation_wavelengths.append(float(excitation))
                if emission is not None:
                    emission_wavelengths.append(float(emission))
            physical_size_x = getattr(pixels, "PhysicalSizeX", None)
            physical_size_y = getattr(pixels, "PhysicalSizeY", None)
            if physical_size_x is not None:
                physical_pixel_sizes.append(float(physical_size_x))
            if physical_size_y is not None:
                physical_pixel_sizes.append(float(physical_size_y))
    except Exception:
        pass

    # Bio-Formats' OMEXML Python wrapper can drop some channel fields for CZI.
    # Fall back to the raw OME XML so classification still sees fluorescence signals.
    if ome_xml:
        xml_values = _extract_channel_fields_from_ome_xml(ome_xml)
        channel_count = channel_count or xml_values["channel_count"]
        pixel_type = pixel_type or xml_values["pixel_type"]
        if not illumination_types:
            illumination_types = list(xml_values["illumination_types"])
        if not fluorophore_names:
            fluorophore_names = list(xml_values["fluorophore_names"])
        if not excitation_wavelengths:
            excitation_wavelengths = list(xml_values["excitation_wavelengths"])
        if not emission_wavelengths:
            emission_wavelengths = list(xml_values["emission_wavelengths"])
        if not channel_names:
            channel_names = list(xml_values["channel_names"])
        if not physical_pixel_sizes:
            physical_pixel_sizes = list(xml_values["physical_pixel_sizes"])

    return {
        "channel_count": channel_count,
        "pixel_type": pixel_type,
        "illumination_types": tuple(illumination_types),
        "fluorophore_names": tuple(fluorophore_names),
        "excitation_wavelengths": tuple(excitation_wavelengths),
        "emission_wavelengths": tuple(emission_wavelengths),
        "channel_names": tuple(channel_names),
        "physical_pixel_sizes": tuple(physical_pixel_sizes),
    }


def _extract_channel_fields_from_ome_xml(ome_xml: str) -> dict[str, Any]:
    channel_count = 0
    pixel_type = None
    illumination_types: list[str] = []
    fluorophore_names: list[str] = []
    excitation_wavelengths: list[float] = []
    emission_wavelengths: list[float] = []
    channel_names: list[str] = []
    physical_pixel_sizes: list[float] = []

    try:
        root = ET.fromstring(ome_xml)
    except ET.ParseError:
        return {
            "channel_count": channel_count,
            "pixel_type": pixel_type,
            "illumination_types": tuple(illumination_types),
            "fluorophore_names": tuple(fluorophore_names),
            "excitation_wavelengths": tuple(excitation_wavelengths),
            "emission_wavelengths": tuple(emission_wavelengths),
            "channel_names": tuple(channel_names),
            "physical_pixel_sizes": tuple(physical_pixel_sizes),
        }

    namespace = {"ome": "http://www.openmicroscopy.org/Schemas/OME/2016-06"}
    pixels = root.find(".//ome:Image/ome:Pixels", namespace)
    if pixels is None:
        return {
            "channel_count": channel_count,
            "pixel_type": pixel_type,
            "illumination_types": tuple(illumination_types),
            "fluorophore_names": tuple(fluorophore_names),
            "excitation_wavelengths": tuple(excitation_wavelengths),
            "emission_wavelengths": tuple(emission_wavelengths),
            "channel_names": tuple(channel_names),
            "physical_pixel_sizes": tuple(physical_pixel_sizes),
        }

    channel_count = int(pixels.attrib.get("SizeC", 0) or 0)
    pixel_type = pixels.attrib.get("Type")
    physical_size_x = pixels.attrib.get("PhysicalSizeX")
    physical_size_y = pixels.attrib.get("PhysicalSizeY")

    for channel in pixels.findall("ome:Channel", namespace):
        name = channel.attrib.get("Name")
        fluor = channel.attrib.get("Fluor")
        illumination = channel.attrib.get("IlluminationType")
        excitation = channel.attrib.get("ExcitationWavelength")
        emission = channel.attrib.get("EmissionWavelength")

        if name:
            channel_names.append(name)
        if fluor:
            fluorophore_names.append(fluor)
        if illumination:
            illumination_types.append(illumination)
        if excitation is not None:
            excitation_wavelengths.append(float(excitation))
        if emission is not None:
            emission_wavelengths.append(float(emission))

    if physical_size_x is not None:
        physical_pixel_sizes.append(float(physical_size_x))
    if physical_size_y is not None:
        physical_pixel_sizes.append(float(physical_size_y))

    return {
        "channel_count": channel_count,
        "pixel_type": pixel_type,
        "illumination_types": tuple(illumination_types),
        "fluorophore_names": tuple(fluorophore_names),
        "excitation_wavelengths": tuple(excitation_wavelengths),
        "emission_wavelengths": tuple(emission_wavelengths),
        "channel_names": tuple(channel_names),
        "physical_pixel_sizes": tuple(physical_pixel_sizes),
    }


def _metadata_properties(metadata: NormalizedCziMetadata) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    if metadata.pixel_type is not None:
        properties["pixel_type"] = metadata.pixel_type
    if metadata.channel_names:
        properties["channel_names"] = metadata.channel_names
    if metadata.fluorophore_names:
        properties["fluorophore_names"] = metadata.fluorophore_names
    if metadata.illumination_types:
        properties["illumination_types"] = metadata.illumination_types
    if metadata.excitation_wavelengths:
        properties["excitation_wavelengths"] = metadata.excitation_wavelengths
    if metadata.emission_wavelengths:
        properties["emission_wavelengths"] = metadata.emission_wavelengths
    if metadata.physical_pixel_sizes:
        properties["physical_pixel_sizes"] = metadata.physical_pixel_sizes
    return properties


def _extract_czifile_metadata(czi_file: Any) -> tuple[dict[str, Any], tuple[int, int]]:
    ome_xml = _extract_czi_xml(czi_file)
    metadata = {
        "channel_count": 0,
        "pixel_type": None,
        "illumination_types": (),
        "fluorophore_names": (),
        "excitation_wavelengths": (),
        "emission_wavelengths": (),
        "channel_names": (),
        "physical_pixel_sizes": (),
    }
    if ome_xml:
        extracted = _extract_channel_fields_from_ome_xml(ome_xml)
        if not any(extracted.values()):
            extracted = _extract_channel_fields_from_image_document_xml(
                ome_xml, czi_file
            )
        metadata.update(extracted)

    dimensions = (0, 0)
    size = getattr(czi_file, "shape", None)
    axes = str(getattr(czi_file, "axes", "") or "")
    if size and axes:
        axis_sizes = {axis.upper(): int(length) for axis, length in zip(axes, size)}
        dimensions = (
            int(axis_sizes.get("X", 0) or 0),
            int(axis_sizes.get("Y", 0) or 0),
        )
    elif size and len(size) >= 2:
        dimensions = (int(size[-1]), int(size[-2]))
    return metadata, dimensions


def _extract_channel_fields_from_image_document_xml(
    xml_text: str, czi_file: Any
) -> dict[str, Any]:
    channel_count = 0
    pixel_type = None
    illumination_types: list[str] = []
    fluorophore_names: list[str] = []
    excitation_wavelengths: list[float] = []
    emission_wavelengths: list[float] = []
    channel_names: list[str] = []
    physical_pixel_sizes: list[float] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {
            "channel_count": channel_count,
            "pixel_type": pixel_type,
            "illumination_types": tuple(illumination_types),
            "fluorophore_names": tuple(fluorophore_names),
            "excitation_wavelengths": tuple(excitation_wavelengths),
            "emission_wavelengths": tuple(emission_wavelengths),
            "channel_names": tuple(channel_names),
            "physical_pixel_sizes": tuple(physical_pixel_sizes),
        }

    if root.tag.lower().endswith("imagedocument"):
        flattened = " ".join(text.strip() for text in root.itertext())
        lowered = flattened.lower()
        if "camera pixel type" in lowered and "uint16" in lowered:
            pixel_type = "uint16"
        if "fluorescencedye" in lowered or "additionaldyeinformation" in lowered:
            illumination_types.append("Epifluorescence")
            for token in ("DAPI", "CD3", "FITC", "TRITC", "Cy3", "Cy5"):
                if token.lower() in lowered and token not in fluorophore_names:
                    fluorophore_names.append(token)
                    channel_names.append(token)
        channel_count = max(channel_count, len(fluorophore_names))
        scaling_x = _extract_image_document_distance(root, "x")
        scaling_y = _extract_image_document_distance(root, "y")
        if scaling_x is not None and scaling_y is not None:
            physical_pixel_sizes = [scaling_x, scaling_y]
        size = getattr(czi_file, "shape", ())
        axes = str(getattr(czi_file, "axes", "") or "")
        if size and axes:
            axis_sizes = {axis.upper(): int(length) for axis, length in zip(axes, size)}
            channel_count = int(axis_sizes.get("C", channel_count) or channel_count)
        if channel_count > 1 and not illumination_types:
            illumination_types.append("Epifluorescence")
        if channel_count > 1 and not fluorophore_names:
            fluorophore_names.extend(
                tuple(f"channel_{index}" for index in range(channel_count))
            )
        if channel_count > 1 and not channel_names:
            channel_names.extend(
                tuple(f"channel_{index}" for index in range(channel_count))
            )
        return {
            "channel_count": channel_count,
            "pixel_type": pixel_type,
            "illumination_types": tuple(illumination_types),
            "fluorophore_names": tuple(fluorophore_names),
            "excitation_wavelengths": tuple(excitation_wavelengths),
            "emission_wavelengths": tuple(emission_wavelengths),
            "channel_names": tuple(channel_names),
            "physical_pixel_sizes": tuple(physical_pixel_sizes),
        }

    return {
        "channel_count": channel_count,
        "pixel_type": pixel_type,
        "illumination_types": tuple(illumination_types),
        "fluorophore_names": tuple(fluorophore_names),
        "excitation_wavelengths": tuple(excitation_wavelengths),
        "emission_wavelengths": tuple(emission_wavelengths),
        "channel_names": tuple(channel_names),
        "physical_pixel_sizes": tuple(physical_pixel_sizes),
    }


def _extract_image_document_distance(root: ET.Element, axis: str) -> float | None:
    axis = axis.lower()
    for element in root.iter():
        attrib = {key.lower(): value for key, value in element.attrib.items()}
        if (
            element.tag.lower().endswith("distance")
            and attrib.get("id", "").lower() == axis
        ):
            value = attrib.get("value")
            if value is None:
                value = element.text
            if value is None:
                first_child = next(iter(element), None)
                value = first_child.text if first_child is not None else None
            if value is None:
                continue
            try:
                return float(value)
            except ValueError:
                return None
    return None


def _extract_czi_xml(czi_file: Any) -> str:
    for attr in ("metadata", "ome_xml", "xml"):
        value = getattr(czi_file, attr, None)
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            return value
    return ""


def _read_czifile_biomarker_region(
    czi_file: Any,
    location: tuple[int, int],
    size: tuple[int, int],
    channel_index: int,
) -> Any:
    x, y = location
    width, height = size
    subblocks: Any = getattr(czi_file, "subblocks", ())
    if callable(subblocks):
        subblocks = subblocks()
    for subblock in cast(Iterable[Any], subblocks):
        directory_entry = getattr(subblock, "directory_entry", None)
        if directory_entry is not None:
            for dimension in getattr(directory_entry, "dimension_entries", ()):
                if getattr(dimension, "dimension", None) == "C":
                    if int(getattr(dimension, "start", -1)) == channel_index:
                        data = (
                            subblock.data()
                            if callable(getattr(subblock, "data", None))
                            else getattr(subblock, "_data", subblock)
                        )
                        start_x = int(
                            getattr(subblock, "dimension_starts", {}).get("X", 0)
                        )
                        start_y = int(
                            getattr(subblock, "dimension_starts", {}).get("Y", 0)
                        )
                        offset_x = x - start_x
                        offset_y = y - start_y
                        if offset_x < 0 or offset_y < 0:
                            raise ValueError(
                                "Requested window starts before matching subblock"
                            )
                        if (
                            hasattr(data, "shape")
                            and len(getattr(data, "shape", ())) >= 2
                        ):
                            return Image.fromarray(
                                data.squeeze()[
                                    offset_y : offset_y + height,
                                    offset_x : offset_x + width,
                                ],
                                mode="L",
                            )
                        return [
                            row[offset_x : offset_x + width]
                            for row in data[offset_y : offset_y + height]
                        ]
        if int(getattr(subblock, "m_index", -1)) == channel_index:
            data = (
                subblock.data()
                if callable(getattr(subblock, "data", None))
                else getattr(subblock, "_data", subblock)
            )
            start_x = int(getattr(subblock, "dimension_starts", {}).get("X", 0))
            start_y = int(getattr(subblock, "dimension_starts", {}).get("Y", 0))
            offset_x = x - start_x
            offset_y = y - start_y
            if offset_x < 0 or offset_y < 0:
                raise ValueError("Requested window starts before matching subblock")
            if hasattr(data, "shape") and len(getattr(data, "shape", ())) >= 2:
                return Image.fromarray(
                    data.squeeze()[
                        offset_y : offset_y + height, offset_x : offset_x + width
                    ],
                    mode="L",
                )
            return [
                row[offset_x : offset_x + width]
                for row in data[offset_y : offset_y + height]
            ]
    raise LookupError(f"Missing subblock for biomarker channel {channel_index}")


def _read_bioformats_biomarker_region(
    reader: Any,
    location: tuple[int, int],
    size: tuple[int, int],
    channel_index: int,
) -> Any:
    x, y = location
    width, height = size
    image_data = reader.read(
        c=channel_index,
        z=0,
        t=0,
        series=0,
        rescale=False,
        XYWH=(x, y, width, height),
    )
    if isinstance(image_data, list):
        return image_data
    if hasattr(image_data, "shape") and len(image_data.shape) == 2:
        return Image.fromarray(image_data, mode="L")
    return Image.fromarray(image_data)
