import json
from typing import Optional

from bs4 import BeautifulSoup
from httpx import RequestError

from wapitiCore.net import Request
from wapitiCore.attack.cms.cms_common import CommonCMS, MSG_TECHNO_VERSIONED
from wapitiCore.net.response import Response
from wapitiCore.definitions.fingerprint_webapp import NAME as WEB_APP_VERSIONED, WSTG_CODE as WEB_WSTG_CODE
from wapitiCore.definitions.fingerprint import NAME as TECHNO_DETECTED, WSTG_CODE
from wapitiCore.main.log import log_blue, logging

MSG_NO_SPIP = "No SPIP Detected"


class ModuleSpipEnum(CommonCMS):
    """Detect SPIP version."""
    PAYLOADS_HASH = "spip_hash_files.json"

    versions = []

    async def check_spip(self, url):

        request = Request(f'{url}', 'GET')
        try:
            response: Response = await self.crawler.async_send(request, follow_redirects=True)
        except RequestError:
            self.network_errors += 1
        else:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for SPIP-related HTML elements, classes, or attributes
            spip_elements = soup.find_all(['spip', 'your_spip_class', 'your_spip_attribute'])

            # Check for SPIP-specific meta tags
            spip_meta_tags = soup.find_all('meta', {'name': ['generator', 'author'], 'content': 'SPIP'})

            # Check for SPIP-specific HTTP headers
            spip_http_headers = {'X-Spip-Cache', 'X-Spip-Version'}  # Add more headers if needed
            has_spip_headers = any(header.lower() in response.headers for header in spip_http_headers)

            # Check for common SPIP directories or files
            common_spip_paths = ['/ecrire/', '/plugins/', '/squelettes/', '/IMG/']
            has_spip_paths = any(path in response.content for path in common_spip_paths)

            has_spip_in_headers = 'composed-by' in response.headers and 'SPIP' in response.headers['composed-by']

            # Check if any of the SPIP indicators were found
            return spip_elements or spip_meta_tags or has_spip_headers or has_spip_paths or has_spip_in_headers


    async def must_attack(self, request: Request, response: Optional[Response] = None):
        if self.finished or request.method == "POST":
            return False

        return request.url == await self.persister.get_root_url()
    
    async def attack(self, request: Request, response: Optional[Response] = None):
        self.finished = True
        request_to_root = Request(request.url)

        if await self.check_spip(request_to_root.url):
            await self.detect_version(self.PAYLOADS_HASH, request_to_root.url)  # Call the method on the instance
            self.versions = sorted(self.versions, key=lambda x: x.split('.')) if self.versions else []

            spip_detected = {
                "name": "SPIP",
                "versions": self.versions,
                "categories": ["CMS SPIP"],
                "groups": ["Content"]
            }

            log_blue(
                MSG_TECHNO_VERSIONED,
                "SPIP",
                self.versions
            )

            if self.versions:
                await self.add_vuln_info(
                    category=WEB_APP_VERSIONED,
                    request=request_to_root,
                    info=json.dumps(spip_detected),
                    wstg=WEB_WSTG_CODE
                )
            await self.add_addition(
                category=TECHNO_DETECTED,
                request=request_to_root,
                info=json.dumps(spip_detected),
                wstg=WSTG_CODE
            )
        else:
            log_blue(MSG_NO_SPIP)
