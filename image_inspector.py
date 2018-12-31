import boto3
import sys
import click
import botocore
import datetime

session = None
instance = None
currentImage = None

# session = boto3.Session(profile_name="default")
# ec2 = session.resource('ec2')

@click.group()
@click.option('--profile', default=None, help="Specify AWS profile. OPTIONAL")
@click.option('--region', default=None, help="Specify AWS region. OPTIONAL")
def cli(profile, region):
    """Manages snapshots"""
    global session, instance, currentImage
    if profile is None:
        profile = 'default'
    session = boto3.Session(profile_name=profile, region_name=region)


def get_instances(project,instance):
    ec2 = session.resource('ec2')    
    instances = []
    if project:
        filters = [{'Name': 'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    if instance:
        instance = [instance]
        instances = ec2.instances.filter(InstanceIds=instance)
    else:
        instances = ec2.instances.all()

    return instances

def get_image(image_id):
    ec2 = session.resource('ec2')  
    currentImage = ec2.Image(image_id)

    return currentImage

def instance_report(instance,currentImage):
    print(', '.join((
        instance.id,
        instance.placement['AvailabilityZone'],
        instance.state['Name']
    )), end="") 
    print(" with image_id {0} details:".format(instance.image_id), end="")
    print(', '.join((
        " [ NAME: {0}".format(currentImage.name),
        "IMAGE_OWNER_ALIES: {0}".format(currentImage.image_owner_alias),
        "CREATION_DATE: {0}".format(currentImage.creation_date),
        "DESCRIPTION: {0}".format(currentImage.description),
        "ENA_SUPPORT: {0}".format(currentImage.ena_support),
        "IMAGE_LOCATION: {0}".format(currentImage.image_location),
        "STATE: {0}".format(currentImage.state),
        "TAGS: {0} ]".format(currentImage.tags),
        "\n"
    )))
    return


@cli.group('instances')
def instances():
    """Commands for instances"""

@instances.command('list')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--image_older_than', default=None, type=int,
    help="Only instances with AMI older than <number> days")


def list_instances(project, image_older_than):
    "List EC2 instances"
    instances = get_instances(project,None)

    if image_older_than:
        print("Please check following instances, with AMI older than {0} days:".format(image_older_than))
        for i in instances:
            currentImage = get_image(i.image_id)
            timeLimit = datetime.datetime.now().replace(microsecond=0) - datetime.timedelta(days=image_older_than)
            image_creation_date = datetime.datetime.strptime(str(currentImage.creation_date)[:-6], '%Y-%m-%dT%H:%M:%S')
        
            if timeLimit > image_creation_date:
                instance_report(i,currentImage)
    else:
        print("Full instances report:")
        for i in instances:
            currentImage = get_image(i.image_id)
            instance_report(i,currentImage)

    return


if __name__ == '__main__':
    cli()