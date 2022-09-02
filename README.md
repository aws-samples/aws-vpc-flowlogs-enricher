## Enrich VPC Flow Logs with resource tags

This repo contains a sample lambda function code that can be used in Kinesis Firehose stream to enrich VPC Flow Log record with additional metadata like resource tags for source and destination IP addresses and, VPC ID, Subnet ID, Interface ID, AZ for destination IP addresses. This data then can be used to identify flows for specific tags, or Source AZ to destination AZ traffic and many more scenarios.

## Prerequisites

* AWS Account
* AWS VPC
* Target S3 bucket before creating Amazon Kinesis Firehose stream

## Architecture:

![VPC Flow Logs enbricher architecture](/images/vpcfl_enricher_architecture.png)

For complete details on how this works, please read the blog post "Enrich VPC Flow Logs with Resource Tags"

## Contributing

We welcome contributions! Please submit a pull request using the PR template.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

## Contact

For bug reports or feature requests, please open a new issue.