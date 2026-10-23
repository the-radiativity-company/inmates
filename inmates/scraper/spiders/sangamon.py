import json
import re

from scrapy import Request
from scrapy import Spider
from scrapy.http import TextResponse

from inmates.scraper.text import text_of


GRID = '/DesktopModules/DnnSharp/ActionGrid/Api.ashx?method=GetData&language=en-US&TabId={tab}&_mid={module}&_tabid={tab}&view=Cards&page={page}'
FORM = '/DesktopModules/MVC/DnnSharp/ActionForm/Load?SCinmateId={id}&openMode=Always&language=en-US'
DETAILS = '/departments/s-z/sheriff/inmate-roster/details?SCinmateId={id}'
TAB_ID = re.compile(r'"tabId":\s*(\d+)')
MODULE_ID = re.compile(r'"moduleId":\s*(\d+)')
EMBEDDED = re.compile(r'"NameStats":\{.*?"value":"((?:[^"\\]|\\.)*)"', re.S)
LABELLED = re.compile(r'^([^:]{1,40}):\s*(.*)$')


class SangamonSpider(Spider):
    """
    Sangamon County's inmate roster on the county's DNN site
    (https://sangamonil.gov/departments/s-z/sheriff/inmate-roster), two
    DnnSharp modules. The roster is an ActionGrid whose data endpoint answers
    a POST with twenty people a page: names, booking number and time,
    prisoner type, release times. Each person's details page is an
    ActionForm whose Load endpoint, given the page's module and tab ids as
    headers, returns the form with the person's record embedded as HTML:
    DOB, charges with statute and class, case numbers, court dates, bonds.

    Both module ids are read from the pages themselves. One record per
    person, the grid's fields plus a 'Details' dict parsed from the form.
    """
    name = 'sangamon'
    custom_settings = {
        'DOWNLOAD_DELAY': 0.25,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []
        self.form = None  # (tab id, module id) of the details form, learnt from the first details page

    def parse(self, response):
        """the roster page: learn the grid's tab and module ids, then ask for page one"""
        tab, module = TAB_ID.search(response.text), MODULE_ID.search(response.text)
        if tab and module:
            yield self.grid_request(response, tab.group(1), module.group(1), 1)

    def grid_request(self, response, tab, module, page):
        return Request(response.urljoin(GRID.format(tab=tab, module=module, page=page)), method='POST', body='{}',
                       headers={'Content-Type': 'application/json'}, callback=self.parse_grid,
                       cb_kwargs={'tab': tab, 'module': module, 'page': page})

    def parse_grid(self, response, tab, module, page):
        data = json.loads(response.text)
        people = [grid_record(result) for result in data.get('results') or []]
        if people and self.form is None:
            # the details form's ids come from a details page; fetch one, then release everyone on this page
            yield response.follow(DETAILS.format(id=people[0]['Id']), callback=self.parse_details_page, cb_kwargs={'people': people})
        else:
            yield from (self.form_request(response, person) for person in people)
        if page < (data.get('totalPages') or 0):
            yield self.grid_request(response, tab, module, page + 1)

    def parse_details_page(self, response, people):
        tab, module = TAB_ID.search(response.text), MODULE_ID.search(response.text)
        if not (tab and module):
            self.logger.error('no form ids on %s; emitting grid records without details', response.url)
            yield from people
            return
        self.form = (tab.group(1), module.group(1))
        yield from (self.form_request(response, person) for person in people)

    def form_request(self, response, person):
        if self.form is None:
            return None
        tab, module = self.form
        return Request(response.urljoin(FORM.format(id=person['Id'])), headers={'TabId': tab, 'ModuleId': module},
                       callback=self.parse_form, cb_kwargs={'person': person})

    def parse_form(self, response, person):
        match = EMBEDDED.search(response.text)
        if match:
            html = TextResponse(url=response.url, body=json.loads(f'"{match.group(1)}"'), encoding='utf-8')
            person['Details'] = parse_details(html)
        yield person


def grid_record(result: dict) -> dict:
    """the grid's field list as a flat dict, keyed by field name, plus the SCinmateId"""
    record = {'Id': result.get('id')}
    for field in result.get('fields') or []:
        value = field.get('Value')
        record[field['Name']] = value if value not in (None, 'None', '') else field.get('FormattedValue') if field['Name'] != 'LastName' else value
    return record


def labelled_lines(selector) -> dict:
    """
    the 'Label: value' lines of a block, split on <br/>. 'DOB: x; Resides in y'
    holds two entries, and 'Booking # 2026-1, ORI: IL0840000' is printed
    without a colon after the number, so the number is picked out by hand.
    """
    found = {}
    for piece in selector.xpath('.//text()').getall():
        for part in re.split(r';\s+(?=[A-Z])', ' '.join(piece.split())):
            part = part.strip()
            number = re.match(r'^(Inmate|Booking) #\s*([^,]*),?$', part)
            match = LABELLED.match(part)
            if number:
                found[f'{number.group(1)} #'] = number.group(2).strip() or None
            elif match:
                found[match.group(1).strip()] = match.group(2).strip() or None
    return found


def parse_details(html) -> dict:
    """the embedded HTML of a details form: a header block, a charges column, a bonds column"""
    header = html.css('.col-md-8')
    details = {'Name': text_of(header.css('h3'))}
    details.update(labelled_lines(header.xpath('./div')))
    details['Charges'] = split_blocks(header[1] if len(header) > 1 else None, 'Charge')
    bonds = html.css('.col-md-4')
    details['Bonds'] = [] if 'No Bonds Listed' in (text_of(bonds) or '') else split_blocks(bonds, 'Bond')
    return details


def split_blocks(selector, kind: str) -> list:
    """<b>Charge 1</b>: text<br/>Label: value<br/>... repeated; one dict per bold heading"""
    if selector is None:
        return []
    blocks = []
    for piece in selector.xpath('.//text()').getall():
        text = ' '.join(piece.split())
        if not text:
            continue
        if re.match(rf'^{kind} (#|\d+$)', text):  # the bold heading: 'Charge 1' or 'Bond #2026-00000908'
            blocks.append({kind: text.split('#', 1)[1].strip() if '#' in text else None})
        elif blocks:
            match = LABELLED.match(text)
            if blocks[-1].get(kind) is None and text.startswith(':') and kind == 'Charge':
                blocks[-1][kind] = text.lstrip(': ').strip()
            elif match:
                blocks[-1][match.group(1).strip()] = match.group(2).strip() or None
    return blocks
