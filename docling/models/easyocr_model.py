import logging
from typing import Iterable

import numpy

from docling.datamodel.base_models import BoundingBox, CoordOrigin, OcrCell, Page
from docling.models.base_ocr_model import BaseOcrModel

_log = logging.getLogger(__name__)


class EasyOcrModel(BaseOcrModel):
    def __init__(self, config):
        super().__init__(config)

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.

        if self.enabled:
            import easyocr

            self.reader = easyocr.Reader(config["lang"])

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:
            ocr_rects = self.get_ocr_rects(page)

            all_ocr_cells = []
            for ocr_rect in ocr_rects:
                high_res_image = page._backend.get_page_image(
                    scale=self.scale, cropbox=ocr_rect
                )
                im = numpy.array(high_res_image)
                result = self.reader.readtext(im)

                del high_res_image
                del im

                cells = [
                    OcrCell(
                        id=ix,
                        text=line[1],
                        confidence=line[2],
                        bbox=BoundingBox.from_tuple(
                            coord=(
                                (line[0][0][0] / self.scale) + ocr_rect.l,
                                (line[0][0][1] / self.scale) + ocr_rect.t,
                                (line[0][2][0] / self.scale) + ocr_rect.l,
                                (line[0][2][1] / self.scale) + ocr_rect.t,
                            ),
                            origin=CoordOrigin.TOPLEFT,
                        ),
                    )
                    for ix, line in enumerate(result)
                ]
                all_ocr_cells.extend(cells)

            ## Remove OCR cells which overlap with programmatic cells.
            filtered_ocr_cells = self.filter_ocr_cells(all_ocr_cells, page.cells)

            page.cells.extend(filtered_ocr_cells)

            # DEBUG code:
            # self.draw_ocr_rects_and_cells(page, ocr_rects)

            yield page
