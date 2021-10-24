# TsuserverDR, a Danganronpa Online server based on tsuserver3, an Attorney Online server
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
# Current project leader: 2018-21 Chrezm/Iuvee <thechrezm@gmail.com>
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

import sys
if r'../..' not in sys.path:
    sys.path.append(r'../..')

from server.constants import Constants
from server.exceptions import AreaError
from server.validate_assets import Validate


class ValidateAreaTemplates(Validate):
    def validate_contents(self, contents, extra_parameters=None):
        if extra_parameters is None:
            extra_parameters = dict()
        server_character_list = extra_parameters.get(
            'server_character_list', None)
        server_default_area_description = extra_parameters.get(
            'server_default_area_description', '')

        for item in contems:
            if 'template_name' not in item:
                if 'apply_template_ranges' not in item or not item['apply_template_ranges']:
                    msg =