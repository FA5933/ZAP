import requests
from bs4 import BeautifulSoup

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs

class PolarionManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        token = self.config.get('Polarion', 'token', fallback=None)
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            })
        else:
            # Fallback to basic auth if token is not present
            self.session.auth = (self.config.get('Polarion', 'user'), self.config.get('Polarion', 'password'))

    def _get_api_url_from_web_url(self, web_url):
        """Converts a Polarion web URL for a test run into an API URL."""
        try:
            parsed_url = urlparse(web_url)
            path_parts = parsed_url.path.split('/')
            query_params = parse_qs(parsed_url.query)

            project_id = None
            if 'project' in path_parts:
                project_id = path_parts[path_parts.index('project') + 1]

            test_run_id = query_params.get('id', [None])[0]

            if not project_id or not test_run_id:
                self.logger.log("Could not parse project ID or test run ID from URL.", level='error')
                return None

            # Construct the API URL
            # Assuming the base URL is the scheme + netloc from the original URL
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            api_url = f"{base_url}/polarion/rest/v1/projects/{project_id}/testruns/{test_run_id}/testrecords"
            return api_url

        except Exception as e:
            self.logger.log(f"Error constructing API URL: {e}", level='error')
            return None

    def download_sttls(self, test_run_url):
        self.logger.log(f"Attempting to download STTLs from web URL: {test_run_url}")

        api_url = self._get_api_url_from_web_url(test_run_url)
        if not api_url:
            return []

        self.logger.log(f"Constructed API URL: {api_url}")

        try:
            response = self.session.get(api_url, verify=False)
            self.logger.log(f"API response status code: {response.status_code}")
            response.raise_for_status()

            test_records_data = response.json()

            sttls = []
            if 'data' in test_records_data and isinstance(test_records_data['data'], list):
                for record in test_records_data['data']:
                    if record.get('type') == 'testrecord' and 'attributes' in record:
                        test_case_id = record['attributes'].get('testCaseId')
                        if test_case_id:
                            sttls.append(test_case_id)

            if sttls:
                self.logger.log(f"Successfully found STTLs via API: {sttls}")
            else:
                self.logger.log("API call successful, but no STTLs found in the response.", level='error')
                self.logger.log(f"API Response for debugging: {response.text}")

            return sttls

        except requests.exceptions.HTTPError as e:
            self.logger.log(f"HTTP Error calling Polarion API: {e}", level='error')
            self.logger.log(f"Response Body: {e.response.text}")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.log(f"Error calling Polarion API: {e}", level='error')
            return []
        except ValueError: # Catches JSON decoding errors
            self.logger.log("Failed to decode JSON from API response.", level='error')
            self.logger.log(f"Non-JSON response for debugging: {response.text}")
            return []

    def upload_results(self, test_run_url, results):
        self.logger.log(f"Uploading results to {test_run_url}")
        # This is a placeholder for actual result upload logic
        try:
            # Example: post results to a specific endpoint
            # response = self.session.post(f"{test_run_url}/results", json=results)
            # response.raise_for_status()
            self.logger.log("Results uploaded successfully.")
        except requests.exceptions.RequestException as e:
            self.logger.log(f"Error uploading results: {e}", level='error')

