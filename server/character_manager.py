# TsuserverDR, a Danganronpa Online server based on tsuserver3, an Attorney Online server
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
# Current project leader: 2018-22 Chrezm/Iuvee <thechrezm@gmail.com>
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

from __future__ import annotations

import typing

from typing import Callable, List, Union

from server.asset_manager import AssetManager
from server.exceptions import CharacterError
from server.validate.characters import ValidateCharacters

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class CharacterManager(AssetManager):
    """
    A manager for characters. Character managers store a list of characters either from a
    loaded file or an adequate Python representation.
    """

    def __init__(self, server: TsuserverDR):
        """
        Create a character manager object.

        Parameters
        ----------
        server: TsuserverDR
            The server this character manager belongs to.
        """

        super().__init__(server)
        self._characters = []
        self._source_file = 'config/characters.yaml'

    def get_name(self) -> str:
        """
        Return `'character list'`.

        Returns
        -------
        str
            `'character list'`.
        """

        return 'character list'

    def get_default_file(self) -> str:
        """
        Return `'config/characters.yaml'`.

        Returns
        -------
        str
            `'config/characters.yaml'`.
        """

        return 'config/characters.yaml'

    def get_loader(self) -> Callable[[str, ], str]:
        """
        Return `self.server.load_characters`.

        Returns
        -------
        Callable[[str, ], str]
            `self.server.load_characters`.
        """

        return self.server.load_characters

    def get_characters(self) -> List[str]:
        """
        Return a copy of the characters managed by this manager.

        Returns
        -------
        List[str]
            Characters managed.
        """

        return self._characters.copy()

    def get_source_file(self) -> Union[str, None]:
        """
        Return the source file of the last character list the manager successfully loaded relative
        to the root directory of the server, or None if the latest loaded character list was loaded
        raw.

        Returns
        -------
        Union[str, None]
            Source file or None.
        """

        return self._source_file

    def get_custom_folder(self) -> str:
        """
        Return `'config/character_lists'`.

        Returns
        -------
        str
            `'config/character_lists'`.
        """

        return 'config/character_lists'

    def validate_file(self, source_file: Union[str, None] = None) -> List[str]:
        if source_file is None:
            source_file = self._source_file

        characters = ValidateCharacters().validate(source_file)
        return characters

    def load_file(self, source_file: str) -> List[str]:
        """
        Set the character list from a given file.

        Parameters
        ----------
        source_file : str
            Relative path from server root folder to character file.

        Returns
        -------
        List[str]
            Characters.

        Raises
        ------
        ServerError.FileInvalidNameError
            If `source_file` includes relative directories.
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        characters = self.validate_file(source_file)
        output = self._load_characters(characters, source_file)
        self._check_structure()
        return output

    def load_raw(self, yaml_contents: List) -> List[str]:
        """
        Load a character list from a YAML representation.

        Parameters
        ----------
        yaml_contents: Dict
            YAML representation.

        Returns
        -------
        List[str]
            Characters.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for characters.
        """

        characters = ValidateCharacters().validate_contents(yaml_contents)
        output = self._load_characters(characters, None)
        self._check_structure()

        return output

    def _load_characters(self, new_list: List[str], source_file: Union[str, None]) -> List[str]:
        self._characters = new_list.copy()
        self._source_file = source_file

        return new_list.copy()

    def is_character(self, character: str) -> bool:
        return character in self._characters

    def is_valid_character_id(self, char_id: Union[int, None]) -> bool:
        return char_id is None or len(self._characters) > char_id >= -1

    def get_character_name(self, char_id: Union[int, None]) -> str:
        if not self.is_valid_character_id(char_id):
            raise CharacterError.CharacterIDNotFoundError
        if char_id == -1:
            return self.server.config['spectator_name']
        if char_id is None:
            return self.server.server_select_name

        return self._characters[char_id]

    def get_character_id_by_name(self, name: str) -> int:
        if name == self.server.config['spectator_name']:
            return -1
        for i, ch in enumerate(self._characters):
            if ch.lower() == name.lower():
                return i
        raise CharacterError.CharacterNotFoundError(f'Character {name} not found.')

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # At least one character
        assert self._characters
