import requests
import json
import configparser

from bs4 import BeautifulSoup as Soup


def read_config_parameters():
    read_config = configparser.ConfigParser()
    read_config.read("credentials.ini")

    return read_config


class Pilots(object):
    def __init__(self):
        self.config = read_config_parameters()
        self.ckan_url = self.config.get("ckan", "ckan_url")
        self.api_token = self.config.get("ckan", "ckan_api_token")
        self.new_pilot = True


    def pilots(self):
        new_pilot = raw_input('Do you want to add a new pilot? y/n (default yes) ') or 'y'

        if new_pilot in ['y', 'Y', 'yes', 'YES', 'Yes']:
            self.create_new_pilot()
        else:
            update_pilot = raw_input('Do you want to edit an existing pilot? y/n (default yes) ') or 'y'

            if update_pilot in ['y', 'Y', 'yes', 'YES']:
                pilot_name = raw_input('Enter pilots name: ')
                print 'You will be updating pilot: ', pilot_name
                path_to_file = raw_input('Enter path to pilots XML file: ')
                print 'Path to pilot XML file is: ', path_to_file

                self.update_pilot_information(pilot_name, path_to_file)


    def create_new_pilot(self):
        data_dict = {}
        self.new_pilot = True

        pilot_name = raw_input('Enter the new pilot name: ')
        data_dict['name'] = pilot_name

        path_to_file = raw_input('Enter path to pilots XML file: ')
        print 'Path to pilot XML file is: ', path_to_file

        # read the xml file
        file_name = open(path_to_file, 'r')
        xml_file = file_name.read()

        soup_resp = Soup(xml_file, 'xml')

        data_dict = self.update_metadata(self.new_pilot, data_dict, soup_resp)

        # create the pilot
        resp = requests.post(self.ckan_url + '/api/action/group_create',
                             data = json.dumps(data_dict),
                             headers = {"Authorization": self.api_token, 'content-type': 'application/json'},
                             verify=False)

        resp = json.loads(resp.content)

        print resp


    def update_pilot_information(self, pilot_name, path_to_file):
        self.new_pilot = False
        # check if the pilot exists on the portal
        pilot = requests.get(self.ckan_url + '/api/action/group_show?id=' + pilot_name, verify=False)
        pilot_info = json.loads(pilot.content)

        if pilot_info['success'] == True:
            data_dict = pilot_info['result']

            # read the xml file
            file_name = open(path_to_file, 'r')
            xml_file = file_name.read()

            soup_resp = Soup(xml_file, 'xml')

            # updated data_dict
            data_dict = self.update_metadata(self.new_pilot, data_dict, soup_resp)

            # update the pilot
            resp = requests.post(self.ckan_url + '/api/action/group_update',
                                 data = json.dumps(data_dict),
                                 headers = {"Authorization": self.api_token, 'content-type': 'application/json'},
                                 verify=False)

            resp = json.loads(resp.content)

            print resp

        else:
            print 'The pilot does not exist on the CKAN portal. Please check the url and the pilot name and try again'


    def update_metadata(self, new_pilot, data_dict, soup_resp):
        item = []
        # read metadata from config file
        metadata = {'purpose', 'individualName', 'organisationName', 'language'}

        for item_node in soup_resp:

            for subitem_node in item_node.findChildren():
                key = subitem_node.name
                value = subitem_node.text.rstrip()

                if key in metadata :
                    item.append({'key': key, 'value': value})

                if key == 'electronicMailAddress':
                    email = value.strip().replace('.', '[dot]').replace('@', '[at]')
                    item.append({'key': 'e-mail', 'value': email})

                if key == 'title':
                    data_dict['title'] = value.strip()

                if key == 'abstract':
                    data_dict['description'] = value

                if key == 'otherConstraints':
                    item.append({'key': 'legal_constraints', 'value': value})

                if key == 'MD_MaintenanceFrequencyCode':
                    item.append({'key': 'update_frequency', 'value': subitem_node['codeListValue']})

                if key == 'beginPosition':
                    item.append({'key': 'begin_position', 'value': value})

                if key == 'endPosition':
                    item.append({'key': 'end_position', 'value': value})


            for lin in item_node.find_all('lineage'):
                for t in lin.findChildren():
                    if t.name == 'statement':
                        value = t.text
                        item.append({'key': 'lineage', 'value': value})

            for ref in item_node.find_all('referenceSystemInfo'):
                for r in ref.findChildren():
                    if r.name == 'CharacterString':
                        value = r.text
                        item.append({'key': 'coordinate_reference_system', 'value': r.text})

            for coordinates in item_node.find_all('EX_GeographicBoundingBox'):
                for c in coordinates.findChildren():
                    if c.name == 'westBoundLongitude':
                        west = c.text.strip()
                    if c.name == 'eastBoundLongitude':
                        east = (c.text).strip()
                    if c.name == 'southBoundLatitude':
                        south = (c.text).strip()
                    if c.name == 'northBoundLatitude':
                        north = (c.text).strip()

                coord_tmp = []
                coord_tmp.append(west)
                coord_tmp.append(east)
                coord_tmp.append(south)
                coord_tmp.append(north)

                coord = '{ \"type\": \"Polygon\", \"coordinates\": [[['+west+','+south+'], ['+east+','+south+'],\
                 ['+east+','+north+'], ['+west+','+north+'], ['+west+', '+south+']]]}'


                item.append({'key': 'extent', 'value': coord.strip()})

            # Resources
            no_of_resources = 0
            resource_data = {'linkage', 'name', 'description'}
            no_resources = len(item_node.find_all('CI_OnlineResource'))
            item.append({'key': 'no_resources', 'value': no_resources})
            item_tmp =[]

            for resource in item_node.find_all('CI_OnlineResource'):
                item_resource = []
                for r in resource.findChildren():
                    key = r.name
                    value = r.text

                    if key in resource_data:
                        item_resource.append({'key': key, 'value': value})

                item.append({'key': 'resource_' +  str(no_resources), 'value': str(item_resource)})
                no_resources -= 1


        item.append({'key': 'language', 'value': 'English'})

        groups = data_dict.get('groups') or None

        if groups is not None:
            for group in groups:
                print "Pilot's parent is: ", group['name']
                parent = raw_input('Do you want to change the parent? y/n (default no) ') or 'n'

                if parent in ['y', 'Y', 'yes', 'YES', 'Yes']:
                    new_parent = raw_input('Enter the name of the new parent: ')
                    group['name'] = new_parent

                    data_dict['groups'] = group
        else:
            parent = raw_input("Set up topic's parent. Enter parent's name: ")
            data_dict['groups'] = [{'capacity': 'public', 'name': parent}]


        ## Sakame da gi postavime dopolnitelnite podatoci
        if new_pilot == False:
            extras = {extra['key']: extra['value'] for extra in data_dict['extras']}

            extra_info = self.update_extra_information(extras)

            for key in extra_info:
                item.append({'key': key, 'value': extra_info[key]})

        else:
            extra_info = self.add_extra_information()

            for key in extra_info:
                item.append({'key': key, 'value': extra_info[key]})


        data_dict['extras'] = ''
        data_dict['extras'] = item

        return data_dict


    def update_extra_information(self, extras=[]):
        extra_info = {}
        topic_types = ['internal', 'external']

        topic_type = extras.get('topic_type') or ''
        collections = extras.get('collections') or ''
        secondary_parent = extras.get('secondary_parent') or ''

        print 'Topic type is: ', topic_type
        topic = raw_input('Do you want to change the topic type? y/n (default no) ') or 'n'

        if topic in ['y', 'Y', 'yes', 'YES', 'Yes']:
            new_topic_type = raw_input('Enter new value for the topic type. Available options: internal or external. ')
            if new_topic_type in topic_types:
                extra_info['topic_type'] =  new_topic_type
        else:
            print 'Topic type will not be changed!'
            extra_info['topic_type'] = topic_type


        print 'List of collections associated with the Pilot: ', collections
        collection = raw_input('Do you want to change the collections list? y/n (default no) ') or 'n'

        if collection in ['y', 'Y', 'yes', 'YES', 'Yes']:
            new_collection = raw_input('NOTE: The collections list should be in the following format: SENTINEL2_L1C, SENTINEL2_L2A.' +
                                        'Enter the new values for collections: ')
            extra_info['collections'] =  new_collection
        else:
            print 'Collections list will not be changed!'
            extra_info['collections'] = collections


        print 'Pilot secondary parent is: ', secondary_parent
        secondary = raw_input('Do you want to associate the pilot with another parent y/n (default no) ') or 'n'

        if secondary in ['y', 'Y', 'yes', 'YES', 'Yes']:
            new_secondary_parent = raw_input('Enter the name of the secondary parent: ')
            extra_info['secondary_parent'] =  new_secondary_parent
        else:
            print 'Secondary parent value will not be changed!'
            extra_info['secondary_parent'] = secondary_parent

        return extra_info



    def add_extra_information(self):
        extra_info = {}
        topic_types = ['internal', 'external']


        new_topic_type = raw_input('Enter value for the topic type. Available options: internal or external. ')
        if new_topic_type in topic_types:
            extra_info['topic_type'] =  new_topic_type



        new_collection = raw_input('NOTE: The collections list should be in the following format: SENTINEL2_L1C, SENTINEL2_L2A.' +
                                    'Enter the values for collections: ')
        extra_info['collections'] =  new_collection

        secondary = raw_input('Do you want to associate the pilot with another parent y/n (default no)? ') or 'n'

        if secondary in ['y', 'Y', 'yes', 'YES', 'Yes']:
            new_secondary_parent = raw_input('Enter the name of the secondary parent: ')
            extra_info['secondary_parent'] =  new_secondary_parent
        else:
            extra_info['secondary_parent'] = ''

        return extra_info


if __name__ == "__main__":
    pilot = Pilots()
    pilot.pilots()