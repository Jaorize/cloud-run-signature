# coding: utf-8

import hashlib
import hmac
import json
from datetime import datetime


class AWSV4Auth:
    def __init__(
        self,
        access_key,
        secret_key,
        host,
        region,
        service,
        method_name,
        timestamp,
        headers={},
        path="",
        payload="",
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.host = host
        self.region = region
        self.service = service
        self.method_name = method_name
        self.headers = headers
        self.timestamp = timestamp
        self.payload = payload
        self.path = path

        # Date and time stamp
        self.xAmzDateTime = self.timestamp.strftime("%Y%m%dT%H%M%SZ")
        self.xAmzDate = self.timestamp.strftime("%Y%m%d")

    def get_headers(self):
        """Return the signed headers including the Authorization header."""
        canonical_request = self.prepare_canonical_url()
        string_to_sign = self.prepare_string_to_sign(canonical_request=canonical_request)
        signing_key = self.get_signature_key(self.secret_key, self.xAmzDate, self.region, self.service)
        signature = self.get_signature(signing_key=signing_key, string_to_sign=string_to_sign)

        # Build Authorization header
        authorization_header = (
            self.algorithm
            + " "
            + "Credential="
            + self.access_key
            + "/"
            + self.credential_scope
            + ", "
            + "SignedHeaders="
            + self.signed_header
            + ", "
            + "Signature="
            + signature
        )
        self.headers["Authorization"] = authorization_header
        return self.headers

    def prepare_canonical_url(self):
        """Create the canonical request for AWS signature."""
        canonical_uri = self.method_name + "\n" + self.path
        canonical_querystring = ""
        canonical_header = ""
        self.signed_header = ""

        # Check if required headers are present
        required_headers = ["host", "x-amz-date"]
        for header in required_headers:
            if header not in self.headers:
                raise ValueError(f"Missing required header: {header}")

        # Build the signed headers list
        sorted_keys = sorted(self.headers, key=str.lower)
        for key in sorted_keys:
            if key and self.headers[key]:  # Check that each key has a defined value
                self.signed_header += key.lower() + ";"
                canonical_header += key.lower() + ":" + self.headers[key] + "\n"

        # Remove trailing semicolon
        self.signed_header = self.signed_header[:-1]

        # Verify and log signed headers
        if not self.signed_header:
            raise ValueError("Signed headers are empty. Ensure that headers are properly defined.")
        print(f"[DEBUG] Signed headers: {self.signed_header}")

        # Hash the payload to include in the request
        payload_hash = hashlib.sha256(
            json.dumps(self.payload).encode("utf-8")
        ).hexdigest()

        # Create canonical request
        canonical_request = (
            canonical_uri
            + "\n"
            + canonical_querystring
            + "\n"
            + canonical_header
            + "\n"
            + self.signed_header
            + "\n"
            + payload_hash
        )
        return canonical_request

    def prepare_string_to_sign(self, canonical_request):
        """Prepare the string to sign based on AWS V4 signature method."""
        self.algorithm = "AWS4-HMAC-SHA256"
        self.credential_scope = (
            self.xAmzDate + "/" + self.region + "/" + self.service + "/" + "aws4_request"
        )
        string_to_sign = (
            self.algorithm
            + "\n"
            + self.xAmzDateTime
            + "\n"
            + self.credential_scope
            + "\n"
            + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        )
        return string_to_sign

    def sign(self, key, msg):
        """Sign a message using HMAC-SHA256 with the provided key."""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def get_signature_key(self, key, date_stamp, region_name, service_name):
        """Create the signing key using a series of HMAC operations."""
        k_date = self.sign(("AWS4" + key).encode("utf-8"), date_stamp)
        k_region = self.sign(k_date, region_name)
        k_service = self.sign(k_region, service_name)
        k_signing = self.sign(k_service, "aws4_request")
        return k_signing

    def get_signature(self, signing_key, string_to_sign):
        """Generate the signature using the signing key and string to sign."""
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature
