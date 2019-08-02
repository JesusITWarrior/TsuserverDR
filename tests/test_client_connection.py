import unittest

from .structures import _TestTsuserverDR

class TestClientConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print('Testing {}...'.format(__file__))
        cls.server = _TestTsuserverDR()
        cls.clients = [None, None, None, None]

    def test_01_client0_connect(self):
        """
        Situation: Client selects the server on the lobby screen.
        """

        self.clients[0] = self.server.create_client()
        c = self.clients[0]
        c.assert_received_packet('decryptor', 34)
        c.assert_received_packet('ID', (0, None, None))
        c.assert_received_packet('FL', ('yellowtext', 'customobjections', 'flipping',
                                        'fastloading', 'noencryption', 'deskmod', 'evidence'))
        c.assert_received_packet('PN', (0, self.server.config['playerlimit']), over=True)
        c.assert_no_ooc()

    def test_02_client1_connect(self):
        """
        Situation: Another client selects the server on the lobby screen.
        """

        self.clients[1] = self.server.create_client()
        c = self.clients[1]
        c.assert_received_packet('decryptor', 34)
        c.assert_received_packet('ID', (1, None, None))
        c.assert_received_packet('FL', ('yellowtext', 'customobjections', 'flipping',
                                        'fastloading', 'noencryption', 'deskmod', 'evidence'))
        c.assert_received_packet('PN', (0, self.server.config['playerlimit']), over=True)
        c.assert_no_ooc()

    def test_03_clients0and1_disconnect(self):
        """
        Situation: Both clients click away.
        """

        # Client 1
        c = self.clients[0]
        c.disconnect()
        c.assert_no_packets()
        c.assert_no_ooc()
        # Check number of clients
        num_clients = len(self.server.client_manager.clients)
        self.assertEqual(num_clients, 1)
        chard_clients = self.server.get_player_count()
        self.assertEqual(chard_clients, 0) # Should be zero as both clients on server select

        # Client 2
        c = self.clients[1]
        c.disconnect()
        c.assert_no_packets()
        c.assert_no_ooc()
        # Check number of clients
        num_clients = len(self.server.client_manager.clients)
        self.assertEqual(num_clients, 0)
        chard_clients = self.server.get_player_count()
        self.assertEqual(chard_clients, 0) # Should be zero as both clients on server select

        self.clients = [None, None, None, None]

    def test_04_client0_joinserver(self):
        """
        Situation: Client clicks and joins server.
        """

        # Starts off as normal
        self.clients[0] = self.server.create_client()
        c = self.clients[0]
        c.assert_received_packet('decryptor', 34)
        c.assert_received_packet('ID', (0, None, None))
        c.assert_received_packet('FL', ('yellowtext', 'customobjections', 'flipping',
                                        'fastloading', 'noencryption', 'deskmod', 'evidence'))
        c.assert_received_packet('PN', (0, self.server.config['playerlimit']), over=True)
        c.assert_no_ooc()

        # But then it carries on
        c.send_command_cts("askchaa#%")
        c.assert_received_packet('SI', (len(self.server.char_list), None, None), over=True)
        c.send_command_cts("RC#%")
        c.assert_received_packet('SC', None, over=True)
        c.send_command_cts("RM#%")
        c.assert_received_packet('SM', None, over=True)
        c.assert_no_ooc()
        c.send_command_cts("RD#%")
        c.assert_received_packet('CharsCheck', None)
        c.assert_received_packet('HP', (1, 10))
        c.assert_received_packet('HP', (2, 10))
        c.assert_received_packet('BN', None)
        c.assert_received_packet('LE', tuple())
        c.assert_received_packet('MM', 1) # ?????
        c.assert_received_packet('OPPASS', None)
        c.assert_received_packet('DONE', tuple())
        c.assert_received_packet('CT', (None, None)) # Area list
        c.assert_received_packet('CT', (None, None)) # MOTD
        c.assert_received_packet('FM', None, over=True) # Music list, again

        host = self.server.config['hostname']
        c.assert_received_ooc(host, None)
        c.assert_received_ooc(host, None, over=True)

        # Since no char yet...
        assert(c.get_char_name() == self.server.config['spectator_name'])

        # Check number of clients
        num_clients = len(self.server.client_manager.clients)
        self.assertEqual(num_clients, 1)
        chard_clients = self.server.get_player_count()
        self.assertEqual(chard_clients, 1) # Should be one now, as SPECTATOR

    def test_05_client1_joinandpickchar(self):
        """
        Situation: Another client joins the server, and picks the first character.
        """

        # Starts off as normal
        self.clients[1] = self.server.create_client()
        c = self.clients[1]
        c.assert_received_packet('decryptor', 34)
        c.assert_received_packet('ID', (1, None, None))
        c.assert_received_packet('FL', ('yellowtext', 'customobjections', 'flipping',
                                        'fastloading', 'noencryption', 'deskmod', 'evidence'))
        c.assert_received_packet('PN', (1, self.server.config['playerlimit']), over=True)
        c.assert_no_ooc()

        # Join server
        c.send_command_cts("askchaa#%")
        c.assert_received_packet('SI', (len(self.server.char_list), None, None), over=True)
        c.send_command_cts("RC#%")
        c.assert_received_packet('SC', None, over=True)
        c.send_command_cts("RM#%")
        c.assert_received_packet('SM', None, over=True)
        c.assert_no_ooc()
        c.send_command_cts("RD#%")
        c.assert_received_packet('CharsCheck', None)
        c.assert_received_packet('HP', (1, 10))
        c.assert_received_packet('HP', (2, 10))
        c.assert_received_packet('BN', None)
        c.assert_received_packet('LE', tuple())
        c.assert_received_packet('MM', 1) # ?????
        c.assert_received_packet('OPPASS', None)
        c.assert_received_packet('DONE', tuple())
        c.assert_received_packet('CT', (None, None)) # Area list
        c.assert_received_packet('CT', (None, None)) # MOTD
        c.assert_received_packet('FM', None, over=True) # Music list, again

        host = self.server.config['hostname']
        c.assert_received_ooc(host, None)
        c.assert_received_ooc(host, None, over=True)

        # Since no char yet...
        assert(c.get_char_name() == self.server.config['spectator_name'])

        # Only now pick char
        c.send_command_cts("CC#1#0#FAKEHDID#%") # Pick char 0
        c.assert_received_packet('PV', (1, 'CID', 0), over=True) # 1 because second client online
        assert(c.get_char_name() == self.server.char_list[0])

        # Check number of clients
        num_clients = len(self.server.client_manager.clients)
        self.assertEqual(num_clients, 2)
        chard_clients = self.server.get_player_count()
        self.assertEqual(chard_clients, 2)

    def test_06_client2_joinandpicksamechar(self):
        """
        Situation: Yet another client joins the server, and first attempts to select the character
        the previous player chose, before trying another one.
        """

        # Starts off as normal
        self.clients[2] = self.server.create_client()
        c = self.clients[2]
        c.assert_received_packet('decryptor', 34)
        c.assert_received_packet('ID', (2, None, None))
        c.assert_received_packet('FL', ('yellowtext', 'customobjections', 'flipping',
                                        'fastloading', 'noencryption', 'deskmod', 'evidence'))
        c.assert_received_packet('PN', (2, self.server.config['playerlimit']), over=True)
        c.assert_no_ooc()

        # Join server
        c.send_command_cts("askchaa#%")
        c.assert_received_packet('SI', (len(self.server.char_list), None, None), over=True)
        c.send_command_cts("RC#%")
        c.assert_received_packet('SC', None, over=True)
        c.send_command_cts("RM#%")
        c.assert_received_packet('SM', None, over=True)
        c.assert_no_ooc()
        c.send_command_cts("RD#%")
        c.assert_received_packet('CharsCheck', None)
        c.assert_received_packet('HP', (1, 10))
        c.assert_received_packet('HP', (2, 10))
        c.assert_received_packet('BN', None)
        c.assert_received_packet('LE', tuple())
        c.assert_received_packet('MM', 1) # ?????
        c.assert_received_packet('OPPASS', None)
        c.assert_received_packet('DONE', tuple())
        c.assert_received_packet('CT', (None, None)) # Area list
        c.assert_received_packet('CT', (None, None)) # MOTD
        c.assert_received_packet('FM', None, over=True) # Music list, again

        host = self.server.config['hostname']
        c.assert_received_ooc(host, None)
        c.assert_received_ooc(host, None, over=True)

        # Since no char yet...
        assert(c.get_char_name() == self.server.config['spectator_name'])

        # Only now pick char
        c.send_command_cts("CC#2#0#FAKEHDID#%") # Attempt to pick char 0
        c.assert_no_packets() # Should not happen as client 1 has char 0
        c.send_command_cts("CC#2#1#FAKEHDID#%") # Attempt to pick char 1
        c.assert_received_packet('PV', (2, 'CID', 1), over=True) # 2 because third client online
        assert(c.get_char_name() == self.server.char_list[1])

        # Check number of clients
        num_clients = len(self.server.client_manager.clients)
        self.assertEqual(num_clients, 3)
        chard_clients = self.server.get_player_count()
        self.assertEqual(chard_clients, 3)

    def test_07_client0_pickchar(self):
        """
        Situation: Player that joined first picks character after previous two players did. First
        attempts both player's characters and an invalid one before going for a valid one.
        """

        c = self.clients[0]
        c.send_command_cts("CC#0#0#FAKEHDID#%") # Attempt to pick char 0
        c.assert_no_packets() # Should not happen as client 1 has char 0
        c.send_command_cts("CC#0#1#FAKEHDID#%") # Attempt to pick char 1
        c.assert_no_packets() # Should not happen as client 2 has char 1
        c.send_command_cts("CC#0#4#FAKEHDID#%") # Attempt to pick char 4
        c.assert_no_packets() # Should not happen as there is no char 4
        c.send_command_cts("CC#0#3#FAKEHDID#%") # Attempt to pick char 3
        c.assert_received_packet('PV', (0, 'CID', 3), over=True) # 0 because first client online
        assert(c.get_char_name() == self.server.char_list[3])

        self.assertEqual(len(self.server.client_manager.clients), 3)
        self.assertEqual(self.server.get_player_count(), 3)

    def test_08_automatedclientcreation(self):
        """
        Situation: Player joins and picks char 2 (automated).
        """

        self.clients[3] = self.server.make_client(2)
        self.assertEqual(len(self.server.client_manager.clients), 4)
        self.assertEqual(self.server.get_player_count(), 4)

    def test_09_middleguydisconnect(self):
        """
        Situation: Client 1 disconnects and reconnects. They should take ID 1 (lowest available)
        and be able to take their old character, which was char_id=0.
        """

        c = self.clients[1]
        c.disconnect()
        c.assert_no_packets()
        c.assert_no_ooc()
        self.assertEqual(len(self.server.client_manager.clients), 3)
        self.assertEqual(self.server.get_player_count(), 3)

        self.clients[1] = self.server.make_client(0)
        self.assertEqual(self.clients[1].id, 1)
        self.assertEqual(len(self.server.client_manager.clients), 4)
        self.assertEqual(self.server.get_player_count(), 4)

    def test_10_twooffourreconnect(self):
        """
        Situation: Clients 0 and 2 disconnect and reconnect. In the process, they end up swapping
        their character choices.
        """

        # c0 had char_id=3
        c = self.clients[0]
        c.disconnect()
        c.assert_no_packets()
        c.assert_no_ooc()
        self.assertEqual(len(self.server.client_manager.clients), 3)
        self.assertEqual(self.server.get_player_count(), 3)

        # c2 had char_id=1
        c = self.clients[2]
        c.disconnect()
        c.assert_no_packets()
        c.assert_no_ooc()
        self.assertEqual(len(self.server.client_manager.clients), 2)
        self.assertEqual(self.server.get_player_count(), 2)

        # Now c0 picks char_id=1
        self.clients[0] = self.server.make_client(1)
        self.assertEqual(self.clients[0].id, 0)
        self.assertEqual(len(self.server.client_manager.clients), 3)
        self.assertEqual(self.server.get_player_count(), 3)

        # And c2 picks char_id=3
        self.clients[2] = self.server.make_client(3)
        self.assertEqual(self.clients[2].id, 2)
        self.assertEqual(len(self.server.client_manager.clients), 4)
        self.assertEqual(self.server.get_player_count(), 4)

    def tearDown(self):
        """
        Check if any packets were unaccounted for.
        """

        for c in self.clients:
            if c:
                c.assert_no_packets()
                c.assert_no_ooc()
        self.clients = None