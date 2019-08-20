# TsuserverDR, a Danganronpa Online server based on tsuserver3, an Attorney Online server
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
# Current project leader: 2018-19 Chrezm/Iuvee <thechrezm@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
Module that contains the AreaManager class, which itself contains the Area subclass.

As Attorney Online clients have no concept of areas, it is the task of the server to perform
all necessary actions in order to simulate different rooms.
"""

import asyncio
import random
import time
import yaml

from server.constants import Constants
from server.exceptions import AreaError
from server.evidence import EvidenceList

class AreaManager:
    """
    Create a new manager for the areas in a server.
    Contains the Area object definition, as well as the server's area list.
    """

    class Area:
        """
        Create a new area for the server.
        """

        def __init__(self, area_id, server, parameters):
            """
            Parameters
            ----------
            area_id : int
                The area ID.
            server : server.TsuServer3
                The server this area belongs to.
            parameters : dict
                Area parameters as specified in the loaded area list.
            """

            self.clients = set()
            self.invite_list = {}
            self.id = area_id
            self.server = server
            self.music_looper = None
            self.next_message_time = 0
            self.hp_def = 10
            self.hp_pro = 10
            self.doc = 'No document.'
            self.status = 'IDLE'
            self.judgelog = []
            self.shoutlog = []
            self.current_music = ''
            self.current_music_player = ''
            self.evi_list = EvidenceList()
            self.is_recording = False
            self.recorded_messages = []
            self.owned = False
            self.ic_lock = False
            self.is_locked = False
            self.is_gmlocked = False
            self.is_modlocked = False
            self.bleeds_to = set()
            self.blood_smeared = False
            self.lights = True
            self.last_ic_messages = list()
            self.parties = set()

            self.name = parameters['area']
            self.background = parameters['background']
            self.bg_lock = parameters['bglock']
            self.evidence_mod = parameters['evidence_mod']
            self.locking_allowed = parameters['locking_allowed']
            self.iniswap_allowed = parameters['iniswap_allowed']
            self.rp_getarea_allowed = parameters['rp_getarea_allowed']
            self.rp_getareas_allowed = parameters['rp_getareas_allowed']
            self.rollp_allowed = parameters['rollp_allowed']
            self.reachable_areas = parameters['reachable_areas']
            self.change_reachability_allowed = parameters['change_reachability_allowed']
            self.default_change_reachability_allowed = parameters['change_reachability_allowed']
            self.gm_iclock_allowed = parameters['gm_iclock_allowed']
            self.afk_delay = parameters['afk_delay']
            self.afk_sendto = parameters['afk_sendto']
            self.lobby_area = parameters['lobby_area']
            self.private_area = parameters['private_area']
            self.scream_range = parameters['scream_range']
            self.restricted_chars = parameters['restricted_chars']
            self.default_description = parameters['default_description']
            self.has_lights = parameters['has_lights']
            self.cbg_allowed = parameters['cbg_allowed']
            self.song_switch_allowed = parameters['song_switch_allowed']

            # Store the current description separately from the default description
            self.description = self.default_description
            # Have a background backup in order to restore temporary background changes
            self.background_backup = self.background
            # Fix comma-separated entries
            self.reachable_areas = Constants.fix_and_setify(self.reachable_areas)
            self.scream_range = Constants.fix_and_setify(self.scream_range)
            self.restricted_chars = Constants.fix_and_setify(self.restricted_chars)

            self.default_reachable_areas = self.reachable_areas.copy()
            self.staffset_reachable_areas = self.reachable_areas.copy()

            if '<ALL>' not in self.reachable_areas:
                self.reachable_areas.add(self.name) #Safety feature, yay sets

            # Make sure only characters that exist are part of the restricted char set
            try:
                for char_name in self.restricted_chars:
                    self.server.char_list.index(char_name)
            except ValueError:
                info = ('Area {} has an unrecognized character {} as a restricted character. '
                        'Please make sure this character exists and try again.'
                        .format(self.name, char_name))
                raise AreaError(info)

        def new_client(self, client):
            """
            Add a client to the client list of the current area.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to add.
            """

            self.clients.add(client)

        def remove_client(self, client):
            """
            Remove a client of the client list of the current area.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to remove.


            Raises
            ------
            KeyError
                If the client is not in the area list.
            """

            try:
                self.clients.remove(client)
            except KeyError:
                if not client.id == -1: # Ignore pre-clients (before getting playercount)
                    info = 'Area {} does not contain client {}'.format(self, client)
                    raise KeyError(info)

            if not self.clients:
                self.unlock()

        def send_command(self, cmd, *args):
            """
            Send a network packet to all clients in the area.

            Parameters
            ----------
            cmd : str
                ID of the packet.
            *args
                Packet arguments.
            """

            for c in self.clients:
                c.send_command(cmd, *args)

        def broadcast_ooc(self, msg):
            """
            Send an OOC server message to this client.

            Parameters
            ----------
            msg : str
                Message to be sent.
            """

            self.send_command('CT', self.server.config['hostname'], msg)

        def change_background(self, bg, validate=True, override_blind=False):
            """
            Change the background of the current area.

            Parameters
            ----------
            bg : str
                New background name.
            validate : bool, optional
                Whether to first determine if background name is listed as a server background
                before changing. Defaults to True.
            override_blind : bool, optional
                Whether to send the intended background to blind people as opposed to the server
                blackout one. Defaults to False (send blackout).

            Raises
            ------
            AreaError
                If the server attempted to validate the background name and failed.
            """

            if validate and bg.lower() not in [name.lower() for name in self.server.backgrounds]:
                raise AreaError('Invalid background name.')

            self.background = bg
            for c in self.clients:
                if c.is_blind and not override_blind:
                    c.send_command('BN', self.server.config['blackout_background'])
                else:
                    c.send_command('BN', bg)

        def get_chars_unusable(self, allow_restricted=False, more_unavail_chars=None):
            """
            Obtain all characters that a player in the current area may NOT change to.

            Parameters
            ----------
            allow_restricted : bool, optional
                Whether to include characters whose usage has been manually restricted in the area.
                Defaults to False.
            more_unavail_chars : set, optional
                Additional characters to mark as taken (and thus unusuable) in the area. Defaults
                to None.

            Returns
            -------
            unavailable : dict
                Character IDs of all unavailable characters in the area.
            """

            if more_unavail_chars is None:
                more_unavail_chars = set()

            unavailable = {x.char_id for x in self.clients if x.char_id is not None}
            unavailable |= more_unavail_chars
            restricted = {self.server.char_list.index(name) for name in self.restricted_chars}

            if not allow_restricted:
                unavailable |= restricted

            return unavailable

        def get_rand_avail_char_id(self, allow_restricted=False,
                                   more_unavail_chars=None):
            """
            Obtain a random available character in the area.

            Parameters
            ----------
            allow_restricted : bool, optional
                Whether to include characters whose usage has been manually restricted in the area.
                Defaults to false.
            more_unavail_chars : set, optional
                Additional characters to mark as taken (and thus unsuable) in the area. Defaults to
                None.

            Returns
            -------
            int
                ID of randomly chosen available character in the area.

            Raises
            -------
            AreaError
                If there are no available characters in the area.
            """

            unusable = self.get_chars_unusable(allow_restricted=allow_restricted,
                                               more_unavail_chars=more_unavail_chars)
            available = {i for i in range(len(self.server.char_list)) if i not in unusable}

            if not available:
                raise AreaError('No available characters.')

            return random.choice(tuple(available))

        def is_char_available(self, char_id, allow_restricted=False, more_unavail_chars=None):
            """
            Decide whether a character can be selected in the current area.

            Parameters
            ----------
            char_id : int
                ID of the character to test.
            allow_restricted : bool, optional
                Whether to include characters whose usage has been manually restricted in the area.
                Defaults to False.
            more_unavail_chars : set, optional
                Additional characters to mark as taken in the area. Defaults to None.

            Returns
            -------
            bool
                True if tested character ID is the spectator ID (which is always available), or
                is not found to be among the area's unusable characters.
            """

            unused = char_id in self.get_chars_unusable(allow_restricted=allow_restricted,
                                                        more_unavail_chars=more_unavail_chars)
            return char_id == -1 or not unused

        def change_doc(self, doc='No document.'):
            """
            Changes the casing document of the area, usually a URL.

            Parameters
            ----------
            doc : str, optional
                New casing document of the area. Defaults to 'No document.'
            """
            self.doc = doc

        def get_evidence_list(self, client):
            """
            Obtain the evidence list for a client.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to target.
            """

            client.evi_list, evi_list = self.evi_list.create_evi_list(client)
            return evi_list

        def broadcast_evidence_list(self):
            """
            Resend all clients in the area their evidence list.

            Packet format: LE#<name>&<desc>&<img>#<name>
            """

            for client in self.clients:
                client.send_command('LE', *self.get_evidence_list(client))

        def change_hp(self, side, val):
            """
            Change a penalty healthbar.

            Parameters
            ----------
            side : int
                Penalty bar to change (1 for def, 2 for pro).
            val : int
                New health value of the penalty bar.

            Raises
            ------
            AreaError
                If an invalid penalty bar or health value was given.
            """
            if not 0 <= val <= 10:
                raise AreaError('Invalid penalty value.')
            if not 1 <= side <= 2:
                raise AreaError('Invalid penalty side.')

            if side == 1:
                self.hp_def = val
            elif side == 2:
                self.hp_pro = val

            self.send_command('HP', side, val)

        def is_iniswap(self, client, anim1, anim2, char):
            """
            Decide if a client is iniswapping or using files outside their claimed character folder.

            Assumes that server permitted iniswaps do not count as iniswaps.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to test.
            anim1 : str
                Location of the preanimation the client used.
            anim2 : str
                Location of the main animation the client used.
            char : str
                Name of the folder the client claims their files are.

            Returns
            -------
            bool
                True if either anim1 or anim2 point to an external location through '../../' or
                their claimed character folder does not match the expected server name and the
                performed iniswap is not in the list of allowed iniswaps by the server.
            """

            if char == client.get_char_name():
                return False

            if '..' in anim1 or '..' in anim2:
                return True
            for char_link in self.server.allowed_iniswaps:
                if client.get_char_name() in char_link and char in char_link:
                    return False
            return True

        def add_to_judgelog(self, client, msg):
            """
            Add a judge action to the judge log of the area.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to record.
            msg : str
                Judge action to record.
            """

            if len(self.judgelog) >= 20:
                self.judgelog = self.judgelog[1:]

            info = '{} | [{}] {} ({}) {}'.format(Constants.get_time(), client.id,
                                                 client.get_char_name(), client.get_ip(), msg)
            self.judgelog.append(info)

        def get_judgelog(self):
            """
            Return the judge log of the area.
            """

            info = '== Judge log of {} ({}) =='.format(self.name, self.id)

            if not self.judgelog:
                info += '\r\nNo judge actions have been performed since the area was loaded.'
            else:
                for log in self.judgelog:
                    info += '\r\n*{}'.format(log)
            return info

        def change_lights(self, new_lights, initiator=None):
            """
            Change the light status of the area and send related announcements.

            This also updates the light status for parties.

            Parameters
            ----------
            new_lights : bool
                New light status
            initiator : server.ClientManager.Client, optional
                Client who triggered the light status change.

            Raises
            ------
            AreaError
                If the new light status matches the current one.
            """

            status = {True: 'on', False: 'off'}
            if self.lights == new_lights:
                raise AreaError('The lights are already turned {}.'.format(status[new_lights]))

            # Change background to match new status
            if new_lights:
                if self.background == self.server.config['blackout_background']:
                    intended_background = self.background_backup
                else:
                    intended_background = self.background
            else:
                if self.background != self.server.config['blackout_background']:
                    self.background_backup = self.background
                intended_background = self.server.config['blackout_background']

            self.change_background(intended_background, validate=False) # Allow restoring custom bg.
            self.lights = new_lights

            # Announce light status change
            if initiator: # If a player initiated the change light sequence, send targeted messages
                if not initiator.is_blind:
                    initiator.send_ooc('You turned the lights {}.'.format(status[new_lights]))
                elif not initiator.is_deaf:
                    initiator.send_ooc('You hear a flicker.')
                else:
                    initiator.send_ooc('You feel a light switch was flipped.')

                initiator.send_ooc_others('The lights were turned {}.'.format(status[new_lights]),
                                          is_staff=False, in_area=True, to_blind=False)
                initiator.send_ooc_others('You hear a flicker.', is_staff=False, in_area=True,
                                          to_blind=True, to_deaf=False)
                initiator.send_ooc_others('{} turned the lights {}.'
                                          .format(initiator.get_char_name(), status[new_lights]),
                                          is_staff=True, in_area=True)
            else: # Otherwise, send generic message
                self.broadcast_ooc('The lights were turned {}.'.format(status[new_lights]))

            # Notify the parties in the area that the lights have changed
            for party in self.parties:
                party.check_lights()

            for c in self.clients:
                c.area_changer.notify_me_blood(self, changed_visibility=True, changed_hearing=False)

        def set_next_msg_delay(self, msg_length):
            """
            Set a message delay for the next IC message in the area based on the length of the
            current message, so new messages sent before this delay expires are discarded.

            Parameters
            ----------
            msg_length : int
                Length of the current message.
            """

            delay = min(3000, 100 + 60 * msg_length)
            self.next_message_time = round(time.time() * 1000.0 + delay)

        def can_send_message(self):
            """
            Decide if an incoming IC message does not violate the area's established delay for
            the previously received IC message.

            Returns
            -------
            bool
                True if the message was sent after the delay was over.
            """

            return (time.time() * 1000.0 - self.next_message_time) > 0

        def play_music(self, name, cid, length=-1):
            """
            Start playing a music track in an area.

            Parameters
            ----------
            name : str
                Name of the track to play.
            cid : int
                Character ID of the player who played the track, or -1 if the server initiated it.
            length : int
                Length of the track in seconds to allow for seamless server-managed looping.
                Defaults to -1 (no looping).
            """
            self.send_command('MC', name, cid)

            if self.music_looper:
                self.music_looper.cancel()
            if length > 0:
                f = lambda: self.play_music(name, -1, length)
                self.music_looper = asyncio.get_event_loop().call_later(length, f)

        def add_music_playing(self, client, name):
            """
            Record the character name and the track they played.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to record.
            name : str
                Track name to record.
            """
            self.current_music_player = client.get_char_name()
            self.current_music = name

        def add_to_shoutlog(self, client, msg):
            """
            Add a shout message to the shout log of the area.

            Parameters
            ----------
            client : server.ClientManager.Client
                Client to record.
            msg : str
                Shout message to record.
            """
            if len(self.shoutlog) >= 20:
                self.shoutlog = self.shoutlog[1:]

            info = '{} | [{}] {} ({}) {}'.format(Constants.get_time(), client.id,
                                                 client.get_char_name(), client.get_ip(), msg)
            self.shoutlog.append(info)

        def add_party(self, party):
            """
            Adds a party to the area's party list.

            Parameters
            ----------
            party : server.PartyManager.Party
                Party to record.

            Raises
            ------
            AreaError:
                If the party is already a part of the party list.
            """

            if party in self.parties:
                raise AreaError('Party {} is already part of the party list of this area.'
                                .format(party.get_id()))
            self.parties.add(party)

        def remove_party(self, party):
            """
            Removes a party from the area's party list.

            Parameters
            ----------
            party : server.PartyManager.Party
                Party to record.

            Raises
            ------
            AreaError:
                If the party is not part of the party list.
            """

            if party not in self.parties:
                raise AreaError('Party {} is not part of the party list of this area.'
                                .format(party.get_id()))
            self.parties.remove(party)

        def get_shoutlog(self):
            """
            Get the shout log of the area.
            """
            info = '== Shout log of {} ({}) =='.format(self.name, self.id)

            if not self.shoutlog:
                info += '\r\nNo shouts have been performed since the area was loaded.'
            else:
                for log in self.shoutlog:
                    info += '\r\n*{}'.format(log)
            return info

        def change_status(self, value):
            """
            Change the casing status of the area to one of predetermined values.

            Parameters
            ----------
            value : str
                New casing status of the area.

            Raises
            ------
            AreaError
                If the new casing status is not among the allowed values.
            """

            allowed_values = ['idle', 'building-open', 'building-full', 'casing-open',
                              'casing-full', 'recess']
            if value.lower() not in allowed_values:
                raise AreaError('Invalid status. Possible values: {}'
                                .format(', '.join(allowed_values)))
            self.status = value.upper()

        def unlock(self):
            """
            Unlock the area so that non-authorized players may now join.
            """

            self.is_locked = False
            if not self.is_gmlocked and not self.is_modlocked:
                self.invite_list = {}

        def gmunlock(self):
            """
            Unlock the area if it had a GM lock so that non-authorized players may now join.
            """

            self.is_gmlocked = False
            self.is_locked = False
            if not self.is_modlocked:
                self.invite_list = {}

        def modunlock(self):
            """
            Unlock the area if it had a mod lock so that non-authorized players may now join.
            """

            self.is_modlocked = False
            self.is_gmlocked = False
            self.is_locked = False
            self.invite_list = {}

        def __repr__(self):
            """
            Return a string representation of the area.

            The string follows the convention 'A::AreaID:AreaName:ClientsInArea'
            """

            return 'A::{}:{}:{}'.format(self.id, self.name, len(self.clients))

    def __init__(self, server):
        """
        Create an area manager object.

        Parameters
        ----------
        server : server.TsuServer3
            The server this area belongs to.
        """

        self.server = server
        self.areas = []
        self.area_names = set()
        self.load_areas()

    def load_areas(self, area_list_file='config/areas.yaml'):
        """
        Load an area list.

        Parameters
        ----------
        area_list_file: str, optional
            Location of the area list to load. Defaults to 'config/areas.yaml'.

        Raises
        ------
        AreaError
            If any one of the following conditions are met:
            * An area has no 'area' or no 'background' tag.
            * An area uses the deprecated 'sound_proof' tag.
            * Two areas have the same name.
            * An area parameter was left deliberately blank as opposed to fully erased.
            * An area has a passage to an undefined area.

        FileNotFound
            If the area list could not be found.
        """

        self.area_names = set()
        current_area_id = 0
        temp_areas = list()
        temp_area_names = set()
        temp_reachable_area_names = set()

        # Check if valid area list file
        with Constants.fopen(area_list_file, 'r') as chars:
            areas = yaml.safe_load(chars)

        def_param = {
            'bglock': False,
            'evidence_mod': 'FFA',
            'locking_allowed': False,
            'iniswap_allowed': False,
            'rp_getarea_allowed': True,
            'rp_getareas_allowed': True,
            'rollp_allowed': True,
            'reachable_areas': '<ALL>',
            'change_reachability_allowed': True,
            'gm_iclock_allowed': True,
            'afk_delay': 0,
            'afk_sendto': 0,
            'lobby_area': False,
            'private_area': False,
            'scream_range': '',
            'restricted_chars': '',
            'default_description': self.server.config['default_area_description'],
            'has_lights': True,
            'cbg_allowed': False,
            'song_switch_allowed': False
            }

        # Create the areas
        for item in areas:
            # Check required parameters
            if 'area' not in item:
                info = 'Area {} has no name.'.format(current_area_id)
                raise AreaError(info)
            if 'background' not in item:
                info = 'Area {} has no background.'.format(item['area'])
                raise AreaError(info)

            # Check unset optional parameters
            for param in def_param:
                if param not in item:
                    item[param] = def_param[param]

            # Check use of backwards incompatible parameters
            if 'sound_proof' in item:
                info = ('The sound_proof property was defined for area {}. '
                        'Support for sound_proof was removed in favor of scream_range. '
                        'Please replace the sound_proof tag with scream_range in '
                        'your area list and try again.'.format(item['area']))
                raise AreaError(info)

            # Avoid having areas with the same name
            if item['area'] in temp_area_names:
                info = ('Two areas have the same name in area list: {}. '
                        'Please rename the duplicated areas and try again.'.format(item['area']))
                raise AreaError(info)

            # Check if any of the items were interpreted as Python Nones (maybe due to empty lines)
            for parameter in item:
                if item[parameter] is None:
                    info = ('Parameter {} is manually undefined for area {}. This can be the case '
                            'due to having an empty parameter line in your area list. '
                            'Please fix or remove the parameter from the area definition and try '
                            'again.'.format(parameter, item['area']))
                    raise AreaError(info)

            temp_areas.append(self.Area(current_area_id, self.server, item))
            temp_area_names.add(item['area'])
            temp_reachable_area_names |= temp_areas[-1].reachable_areas
            current_area_id += 1

        # Check if a reachable area is not an area name
        # Can only be done once all areas are created

        unrecognized_areas = temp_reachable_area_names-temp_area_names-{'<ALL>'}
        if unrecognized_areas != set():
            info = ('Unrecognized area names defined as reachable areas in area list file: {}. '
                    'Please rename the affected areas and try again.'.format(unrecognized_areas))
            raise AreaError(info)

        # Only once all areas have been created, actually set the corresponding values
        # Helps avoiding junk area lists if there was an error
        old_areas = self.areas
        self.areas = temp_areas
        self.area_names = temp_area_names

        # If the default area ID is now past the number of available areas, reset it back to zero
        if self.server.default_area >= len(self.areas):
            self.server.default_area = 0

        for area in old_areas:
            # Decide whether the area still exists or not
            try:
                new_area = self.get_area_by_name(area.name)
                remains = True
            except AreaError:
                new_area = self.default_area()
                remains = False

            # Move existing clients to new corresponding area (or to default area if their previous
            # area no longer exists).
            for client in area.clients.copy():
                # Check if current char is available
                if new_area.is_char_available(client.char_id):
                    new_char_id = client.char_id
                else:
                    try:
                        new_char_id = new_area.get_rand_avail_char_id()
                    except AreaError:
                        new_char_id = -1

                if remains:
                    message = 'Area list reload. Moving you to the new {}.'
                else:
                    message = ('Area list reload. Your previous area no longer exists. Moving you '
                               'to the server default area {}.')

                client.send_ooc(message.format(new_area.name))
                client.change_area(new_area, ignore_checks=True, change_to=new_char_id,
                                   ignore_notifications=True)

            # Move parties (independently)
            for party in area.parties.copy():
                party.area = new_area
                new_area.add_party(party)

        # Update the server's area list only once everything is successful
        self.server.old_area_list = self.server.area_list
        self.server.area_list = area_list_file

    def default_area(self):
        """
        Return the Area object corresponding to the server's default area.
        """

        return self.areas[self.server.default_area]

    def get_area_by_name(self, name):
        """
        Return the Area object corresponding to the area that has the given name.

        Parameters
        ----------
        name : str
            Area name to look for.

        Raises
        ------
        AreaError
            If no area has the given name.
        """

        for area in self.areas:
            if area.name == name:
                return area
        raise AreaError('Area not found.')

    def get_area_by_id(self, num):
        """
        Return the Area object corresponding to the area that has the given ID.

        Parameters
        ----------
        id : num
            Area ID to look for.

        Raises
        ------
        AreaError
            If no area has the given ID.
        """

        for area in self.areas:
            if area.id == num:
                return area
        raise AreaError('Area not found.')
