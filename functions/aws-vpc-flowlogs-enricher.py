# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import base64
import json
import boto3
import io
from collections import OrderedDict


ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')

def lambda_handler(event, context):
    """
    This function processes vpc flow log records buffered by Amazon Kinesis Data Firehose. Each record is enriched with additional metadata 
    like resource tags for source & destination IP address. VPC ID, Region, Subnet ID, Interface ID etc. for destination IP address.
    """
    output = []
    instance_id=None
    src_tag_prefix='src-tag-'
    dst_tag_prefix='dst-tag-'
    dst_prefix='dst-'
    
    vpc_fl_header = "account-id action az-id bytes dstaddr dstport end flow-direction instance-id interface-id log-status packets pkt-dst-aws-service pkt-dstaddr pkt-src-aws-service pkt-srcaddr protocol region srcaddr srcport start sublocation-id sublocation-type subnet-id tcp-flags traffic-path type version vpc-id"

    for record in event['records']:
        # Decode the payload with utf-8 to read the values from the record and enrich it
        payload = base64.b64decode(record['data']).decode('utf-8')

        # Custom processing to enrich the payload
        try:
            json_payload=json.loads(payload)
            
            # Original record from VPC Flow Logs is separated by space delimiter
            flow_log_record=json_payload["message"].split(" ")

            record_dict=OrderedDict({"account-id": flow_log_record[0], "action": flow_log_record[1], "az-id": flow_log_record[2], "bytes": flow_log_record[3], "dstaddr": flow_log_record[4], "dstport": flow_log_record[5], \
            "end": flow_log_record[6], "flow-direction": flow_log_record[7], "instance-id": flow_log_record[8], "interface-id": flow_log_record[9], "log-status": flow_log_record[10], \
            "packets": flow_log_record[11], "pkt-dst-aws-service": flow_log_record[12], "pkt-dstaddr": flow_log_record[13], "pkt-src-aws-service": flow_log_record[14], \
            "pkt-srcaddr": flow_log_record[15], "protocol": flow_log_record[16], "region": flow_log_record[17], "srcaddr": flow_log_record[18], "srcport": flow_log_record[19], \
            "start": flow_log_record[20], "sublocation-id": flow_log_record[21], "sublocation-type": flow_log_record[22], "subnet-id": flow_log_record[23], "tcp-flags": flow_log_record[24], \
            "traffic-path": flow_log_record[25], "type": flow_log_record[26], "version": flow_log_record[27], "vpc-id": flow_log_record[28]})
            
            instance_id = record_dict['instance-id']
            destination_addr = record_dict['dstaddr']

            # Get the resource tags for instance id from the log record
            if instance_id:
                if len(instance_id) > 0 and instance_id.strip() != "-":
                    tags = get_resource_tags(instance_id)
                    if tags:
                        for tag in tags:
                            record_dict[src_tag_prefix + tag["Key"]]=tag["Value"]

            # Get the resource tags, VPC id, AZ, Subnet, Interface and Instance id for destination ip address
            if destination_addr:
                if len(destination_addr) > 0 and destination_addr.strip() != "-":
                    ip_metadata = get_resource_id(destination_addr)
                    if ip_metadata and ip_metadata.get('tags'):
                        for tag in ip_metadata['tags']:
                            record_dict[dst_tag_prefix + tag["Key"]]=tag["Value"]
                            
                        # Add vpc-id, az-id, subnet-id, interface-id, instance-id for destination ip address
                        record_dict[dst_prefix + "vpc-id"] = ip_metadata["vpc-id"]
                        record_dict[dst_prefix + "az-id"] = ip_metadata["az-id"]
                        record_dict[dst_prefix + "subnet-id"] = ip_metadata["subnet-id"]
                        record_dict[dst_prefix + "interface-id"] = ip_metadata["interface-id"]
                        record_dict[dst_prefix + "instance-id"] = ip_metadata["instance-id"]

            # Finally modify the payload with enriched record
            payload=json.dumps(record_dict) + "\n"
        except Exception as ex:
            print('Could not process record, Exception: ', ex)
            output_record = {
                'recordId': record['recordId'],
                'result': 'ProcessingFailed',
                'data': base64.b64encode(payload.encode('utf-8')).decode('utf-8')
            }
        else:
            # Assign the enriched record to the output_record for Kinesis to process it further
            output_record = {
                'recordId': record['recordId'],
                'result': 'Ok',
                'data': base64.b64encode(payload.encode('utf-8')).decode('utf-8')
            }
            
        output.append(output_record)


    print('Successfully processed {} records.'.format(len(event['records'])))

    return {'records': output}
    
def get_resource_tags(resource_id):
    """
    This function fetches resource tags for resource_id parameter using boto3
    """
    resource_tags=None
    try:
        ec2 = boto3.resource('ec2')
        ec2instance = ec2.Instance(resource_id)
        resource_tags=ec2instance.tags
    except Exception as ex:
        print('Exception get_resource_tags: ', ex)
        
    return resource_tags

def get_resource_id(ip_address):
    """
    This function fetches resource id for ip_address parameter and then fetches resource tags, vpc id, subnet id etc.
    for resource_id using boto3
    """
    resource_id_tags=None
    ip_metadata = {}
    
    try:
        instance=ec2_client.describe_instances(Filters=[{'Name': 'private-ip-address', 'Values': [ip_address]},])

        if 'Reservations' in instance and len(instance['Reservations']) > 0:
            resource_id=instance['Reservations'][0]['Instances'][0]['InstanceId']
            subnet_id=instance['Reservations'][0]['Instances'][0]['SubnetId']
            az_id=instance['Reservations'][0]['Instances'][0]['Placement']['AvailabilityZone']
            eni=instance['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['NetworkInterfaceId']
            vpc_id=instance['Reservations'][0]['Instances'][0]['VpcId']
            resource_id_tags=get_resource_tags(resource_id)
            ip_metadata["tags"] = resource_id_tags
            ip_metadata["az-id"] = az_id
            ip_metadata["interface-id"] = eni
            ip_metadata["instance-id"]= resource_id
            ip_metadata["subnet-id"]=subnet_id
            ip_metadata["vpc-id"]=vpc_id

    except Exception as ex:
        print('Exception get_resource_id: ', ex)
        
    return ip_metadata