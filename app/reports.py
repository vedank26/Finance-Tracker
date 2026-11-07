import csv
import io
import logging
import re
import uuid
from datetime import date
from flask import current_app
import boto3
from botocore.exceptions import ClientError
from app.models import Transaction
from app.analytics import get_month_date_range

logger = logging.getLogger(__name__)

REPORT_KEY_PATTERN = re.compile(r'^monthly-reports/user-(\d+)/(\d{4}-\d{2})/report-([a-f0-9\-]+)\.csv$')


def sanitize_csv_cell(value):
    """
    Sanitize a text cell to prevent spreadsheet formula injection (CWE-1236).
    If a text value starts with '=', '+', '-', '@', '\t', or '\r' (even after leading whitespace
    or control characters), prefix it with a single quote (').
    Preserves legitimate numeric values (such as negative numbers) without prepending quotes.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    s = str(value)
    stripped = s.lstrip(' \t\r\n\v\f')
    if s.startswith(('\t', '\r')) or (stripped and stripped[0] in ('=', '+', '-', '@')):
        return f"'{s}"
    return s


def parse_and_validate_month(month_str):
    """
    Validates and parses a YYYY-MM string.
    Returns (year, month) as integers, or raises ValueError.
    """
    if not month_str or not isinstance(month_str, str):
        raise ValueError("Month is required.")
    month_str = month_str.strip()
    match = re.match(r'^(\d{4})-(\d{2})$', month_str)
    if not match:
        raise ValueError("Month must be in YYYY-MM format.")
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        raise ValueError("Month must be between 01 and 12.")
    if year < 1900 or year > 2100:
        raise ValueError("Year is out of valid range.")
    return year, month


def generate_monthly_csv(user_id, year, month):
    """
    Queries transactions for user_id within the half-open range:
      start_date <= transaction.date < next_month_start
    and returns a sanitized CSV string.
    """
    start_date, next_month_start = get_month_date_range(year=year, month=month)
    
    transactions = (
        Transaction.query
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date < next_month_start
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['Date', 'Description', 'Category', 'Type', 'Amount'])

    for t in transactions:
        writer.writerow([
            t.date.strftime('%Y-%m-%d') if t.date else '',
            sanitize_csv_cell(t.description or ''),
            sanitize_csv_cell(t.category or ''),
            t.type or '',
            f"{t.amount:.2f}" if t.amount is not None else '0.00'
        ])

    return output.getvalue()


def get_s3_client():
    """
    Instantiates a boto3 S3 client using standard AWS credential chain.
    """
    region = current_app.config.get('AWS_REGION', 'us-east-1') or 'us-east-1'
    return boto3.client('s3', region_name=region)


def upload_report_to_s3(user_id, year, month, csv_content):
    """
    Uploads a generated CSV report to a private Amazon S3 bucket with AES256 encryption.
    Returns (success: bool, object_key_or_error: str, presigned_url: Optional[str]).
    """
    bucket = current_app.config.get('S3_REPORT_BUCKET')
    if not bucket:
        return (
            False,
            "Amazon S3 storage is not configured. Set S3_REPORT_BUCKET in your environment to enable monthly reports.",
            None
        )

    object_key = f"monthly-reports/user-{user_id}/{year:04d}-{month:02d}/report-{uuid.uuid4().hex}.csv"

    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=csv_content.encode('utf-8'),
            ContentType='text/csv',
            ServerSideEncryption='AES256'
        )

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': object_key},
            ExpiresIn=900
        )
        return True, object_key, presigned_url
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'UnknownClientError')
        logger.error("S3 ClientError uploading monthly report: %s", error_code)
        return False, f"Failed to upload report to Amazon S3: {error_code}", None
    except Exception as e:
        logger.error("Unexpected error uploading monthly report to S3: %s", type(e).__name__)
        return False, f"Failed to upload report to Amazon S3: {type(e).__name__}", None


def validate_user_report_key(user_id, object_key):
    """
    Validates that object_key matches the strict monthly report key format
    and belongs to the given user_id.
    Rejects malformed keys, directory traversal ('..'), absolute paths, or mismatched user IDs.
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    if not object_key or not isinstance(object_key, str):
        return False, "Invalid report key format."

    if '..' in object_key or '\\' in object_key:
        return False, "Path traversal sequence detected."

    match = REPORT_KEY_PATTERN.match(object_key)
    if not match:
        return False, "Report key does not match the required format."

    key_user_id = int(match.group(1))
    if key_user_id != int(user_id):
        return False, "Unauthorized access to report."

    return True, None


def generate_report_presigned_url(user_id, object_key, expires_in=900):
    """
    Validates user ownership of object_key and generates a presigned S3 download URL.
    Raises PermissionError or ValueError or RuntimeError if validation or config fails.
    """
    is_valid, error = validate_user_report_key(user_id, object_key)
    if not is_valid:
        raise PermissionError(error)

    bucket = current_app.config.get('S3_REPORT_BUCKET')
    if not bucket:
        raise RuntimeError("Amazon S3 storage is not configured.")

    s3_client = get_s3_client()
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': object_key},
        ExpiresIn=expires_in
    )
