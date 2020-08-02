from io import BytesIO
from io import StringIO
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from scrapy import Spider
from subprocess import run as run_proc


class AdamsRoster(Spider):
    name = 'adams'

    def parse(self, response):
        pdf_text = handle_pdf(BytesIO(response.body))
        pdf_lines = pdf_text.split('\n')

        #-- predicates ---
        starts_with_digit = lambda s: s[0].isdigit() if len(s) else False
        has_more_than_digit = lambda s: len(s.split()) > 1
        text_is_uppercased = lambda s: s.split()[1:][0].isupper() if s.split()[1:] else False
        #-----------------

        for line in pdf_lines:
            if starts_with_digit(line) and has_more_than_digit(line) and text_is_uppercased(line):
                tokens = line.split()
                yield {
                    'Name': f'{tokens[1].title()} {tokens[2].title()}',
                    'Gender': None,
                    'Height': None,
                    'HousingFacility': None,
                    'Race': None,
                    'MultipleBookings': None,
                    'InCustody': None,
                    'Weight': None
                }


def handle_pdf(buffer: BytesIO, codec: str = 'utf-8'):
    rsrcmgr = PDFResourceManager()  # shared context for resources
    sio = StringIO()
    laparams = LAParams()  # "layout params" for formatting output
    device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for page in PDFPage.get_pages(buffer):
        interpreter.process_page(page)

    text = sio.getvalue()

    device.close()
    sio.close()

    return text
