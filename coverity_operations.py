import json
from collections import namedtuple

f = open('config/coverity_sample.json')
input_json = json.load(f)


def jsonObjectDecoder(inputJson):
    return namedtuple('X', inputJson.keys())(*inputJson.values())


def createProject(configServiceClient):
    projectSpec = configServiceClient.client.factory.create('projectSpecDataObj')
    projectSpecJson = json.dumps(input_json['projectSpecDataObj'])
    projectSpec = json.loads(projectSpecJson, object_hook=projectSpec)
    # projectSpec = json.loads(projectSpecJson, object_hook=jsonObjectDecoder)
    results = configServiceClient.client.service.createProject(projectSpec)
    return results


def createStream(configServiceClient):
    streamSpec = configServiceClient.client.factory.create('streamSpecDataObj')
    streamSpec.name = input_json['streamSpecDataObj']
    results = configServiceClient.client.service.createProject(streamSpec)
    return results


def createRole(configServiceClient):
    roleSpec = configServiceClient.client.factory.create('roleSpecDataObj')
    roleSpec.name = input_json['roleSpecDataObj']['name']
    roleSpec.description = input_json['roleSpecDataObj']['description']
    results = configServiceClient.client.service.createProject(roleSpec)
    return results
