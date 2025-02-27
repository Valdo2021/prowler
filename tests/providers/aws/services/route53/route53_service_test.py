from unittest.mock import patch

import botocore
from boto3 import client, session
from moto import mock_logs, mock_route53

from prowler.providers.aws.lib.audit_info.audit_info import AWS_Audit_Info
from prowler.providers.aws.services.route53.route53_service import Route53

# Mock Test Region
AWS_REGION = "us-east-1"

# Mocking Access Analyzer Calls
make_api_call = botocore.client.BaseClient._make_api_call


def mock_make_api_call(self, operation_name, kwarg):
    """We have to mock every AWS API call using Boto3"""
    if operation_name == "DescribeDirectories":
        return {}
    if operation_name == "ListTagsForResource":
        return {
            "ResourceTagSet": {
                "ResourceType": "hostedzone",
                "ResourceId": "test",
                "Tags": [
                    {"Key": "test", "Value": "test"},
                ],
            }
        }
    return make_api_call(self, operation_name, kwarg)


# Patch every AWS call using Boto3 and generate_regional_clients to have 1 client
@patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
class Test_Route53_Service:
    # Mocked Audit Info
    def set_mocked_audit_info(self):
        audit_info = AWS_Audit_Info(
            session_config=None,
            original_session=None,
            audit_session=session.Session(
                profile_name=None,
                botocore_session=None,
            ),
            audited_account=None,
            audited_account_arn=None,
            audited_user_id=None,
            audited_partition="aws",
            audited_identity_arn=None,
            profile=None,
            profile_region=AWS_REGION,
            credentials=None,
            assumed_role_info=None,
            audited_regions=None,
            organizations_metadata=None,
            audit_resources=None,
            mfa_enabled=False,
        )
        return audit_info

    # Test Route53 Client
    @mock_route53
    def test__get_client__(self):
        route53 = Route53(self.set_mocked_audit_info())
        assert route53.client.__class__.__name__ == "Route53"

    # Test Route53 Session
    @mock_route53
    def test__get_session__(self):
        route53 = Route53(self.set_mocked_audit_info())
        assert route53.session.__class__.__name__ == "Session"

    # Test Route53 Service
    @mock_route53
    def test__get_service__(self):
        route53 = Route53(self.set_mocked_audit_info())
        assert route53.service == "route53"

    @mock_route53
    @mock_logs
    def test__list_hosted_zones__private_with_logging(self):
        # Create Hosted Zone
        r53_client = client("route53", region_name=AWS_REGION)
        hosted_zone_name = "testdns.aws.com."
        response = r53_client.create_hosted_zone(
            Name=hosted_zone_name,
            CallerReference=str(hash("foo")),
            HostedZoneConfig={"Comment": "", "PrivateZone": True},
        )
        hosted_zone_id = response["HostedZone"]["Id"].replace("/hostedzone/", "")
        hosted_zone_name = response["HostedZone"]["Name"]
        # CloudWatch Client
        logs_client = client("logs", region_name=AWS_REGION)
        log_group_name = "test-log-group"
        _ = logs_client.create_log_group(logGroupName=log_group_name)
        log_group_arn = logs_client.describe_log_groups()["logGroups"][0]["arn"]

        # Create Query Logging Config
        response = r53_client.create_query_logging_config(
            HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn
        )

        # Set partition for the service
        route53 = Route53(self.set_mocked_audit_info())
        assert len(route53.hosted_zones) == 1
        assert route53.hosted_zones[hosted_zone_id]
        assert route53.hosted_zones[hosted_zone_id].id == hosted_zone_id
        assert (
            route53.hosted_zones[hosted_zone_id].arn
            == f"arn:aws:route53:::hostedzone/{hosted_zone_id}"
        )
        assert route53.hosted_zones[hosted_zone_id].name == hosted_zone_name
        assert route53.hosted_zones[hosted_zone_id].private_zone
        assert route53.hosted_zones[hosted_zone_id].logging_config
        assert (
            route53.hosted_zones[hosted_zone_id].logging_config.cloudwatch_log_group_arn
            == log_group_arn
        )
        assert route53.hosted_zones[hosted_zone_id].region == AWS_REGION
        assert route53.hosted_zones[hosted_zone_id].tags == [
            {"Key": "test", "Value": "test"},
        ]

    @mock_route53
    @mock_logs
    def test__list_hosted_zones__public_with_logging(self):
        # Create Hosted Zone
        r53_client = client("route53", region_name=AWS_REGION)
        hosted_zone_name = "testdns.aws.com."
        response = r53_client.create_hosted_zone(
            Name=hosted_zone_name,
            CallerReference=str(hash("foo")),
            HostedZoneConfig={"Comment": "", "PrivateZone": False},
        )
        hosted_zone_id = response["HostedZone"]["Id"].replace("/hostedzone/", "")
        hosted_zone_name = response["HostedZone"]["Name"]
        # CloudWatch Client
        logs_client = client("logs", region_name=AWS_REGION)
        log_group_name = "test-log-group"
        _ = logs_client.create_log_group(logGroupName=log_group_name)
        log_group_arn = logs_client.describe_log_groups()["logGroups"][0]["arn"]

        # Create Query Logging Config
        response = r53_client.create_query_logging_config(
            HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn
        )

        # Set partition for the service
        route53 = Route53(self.set_mocked_audit_info())
        assert len(route53.hosted_zones) == 1
        assert route53.hosted_zones[hosted_zone_id]
        assert route53.hosted_zones[hosted_zone_id].id == hosted_zone_id
        assert (
            route53.hosted_zones[hosted_zone_id].arn
            == f"arn:aws:route53:::hostedzone/{hosted_zone_id}"
        )
        assert route53.hosted_zones[hosted_zone_id].name == hosted_zone_name
        assert not route53.hosted_zones[hosted_zone_id].private_zone
        assert route53.hosted_zones[hosted_zone_id].logging_config
        assert (
            route53.hosted_zones[hosted_zone_id].logging_config.cloudwatch_log_group_arn
            == log_group_arn
        )
        assert route53.hosted_zones[hosted_zone_id].region == AWS_REGION

    @mock_route53
    @mock_logs
    def test__list_hosted_zones__private_without_logging(self):
        # Create Hosted Zone
        r53_client = client("route53", region_name=AWS_REGION)
        hosted_zone_name = "testdns.aws.com."
        response = r53_client.create_hosted_zone(
            Name=hosted_zone_name,
            CallerReference=str(hash("foo")),
            HostedZoneConfig={"Comment": "", "PrivateZone": True},
        )
        hosted_zone_id = response["HostedZone"]["Id"].replace("/hostedzone/", "")
        hosted_zone_name = response["HostedZone"]["Name"]

        # Set partition for the service
        route53 = Route53(self.set_mocked_audit_info())
        assert len(route53.hosted_zones) == 1
        assert route53.hosted_zones[hosted_zone_id]
        assert route53.hosted_zones[hosted_zone_id].id == hosted_zone_id
        assert (
            route53.hosted_zones[hosted_zone_id].arn
            == f"arn:aws:route53:::hostedzone/{hosted_zone_id}"
        )
        assert route53.hosted_zones[hosted_zone_id].name == hosted_zone_name
        assert route53.hosted_zones[hosted_zone_id].private_zone
        assert not route53.hosted_zones[hosted_zone_id].logging_config
        assert route53.hosted_zones[hosted_zone_id].region == AWS_REGION

    @mock_route53
    @mock_logs
    def test__list_hosted_zones__public_without_logging(self):
        # Create Hosted Zone
        r53_client = client("route53", region_name=AWS_REGION)
        hosted_zone_name = "testdns.aws.com."
        response = r53_client.create_hosted_zone(
            Name=hosted_zone_name,
            CallerReference=str(hash("foo")),
            HostedZoneConfig={"Comment": "", "PrivateZone": False},
        )
        hosted_zone_id = response["HostedZone"]["Id"].replace("/hostedzone/", "")
        hosted_zone_name = response["HostedZone"]["Name"]

        # Set partition for the service
        route53 = Route53(self.set_mocked_audit_info())
        assert len(route53.hosted_zones) == 1
        assert route53.hosted_zones[hosted_zone_id]
        assert route53.hosted_zones[hosted_zone_id].id == hosted_zone_id
        assert (
            route53.hosted_zones[hosted_zone_id].arn
            == f"arn:aws:route53:::hostedzone/{hosted_zone_id}"
        )
        assert route53.hosted_zones[hosted_zone_id].name == hosted_zone_name
        assert not route53.hosted_zones[hosted_zone_id].private_zone
        assert not route53.hosted_zones[hosted_zone_id].logging_config

        assert route53.hosted_zones[hosted_zone_id].region == AWS_REGION

    @mock_route53
    def test__list_resource_record_sets__(self):
        # Create Hosted Zone
        r53_client = client("route53", region_name=AWS_REGION)
        zone = r53_client.create_hosted_zone(
            Name="testdns.aws.com", CallerReference=str(hash("foo"))
        )
        zone_id = zone["HostedZone"]["Id"]

        r53_client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "foo.bar.testdns.aws.com",
                            "Type": "A",
                            "ResourceRecords": [{"Value": "1.2.3.4"}],
                        },
                    }
                ]
            },
        )

        # Set partition for the service
        route53 = Route53(self.set_mocked_audit_info())
        assert (
            len(route53.record_sets) == 3
        )  # Default NS and SOA records plus the A record just created
        for set in route53.record_sets:
            if set.type == "A":
                assert set.name == "foo.bar.testdns.aws.com."
                assert set.type == "A"
                assert not set.is_alias
                assert set.records == ["1.2.3.4"]
                assert set.hosted_zone_id == zone_id.replace("/hostedzone/", "")
                assert set.region == AWS_REGION
