"""Library for multiplayer split games.

Servers should start and stay running.
"""

import game
import socket
import threading


PORT = 6006


class RemotePlayer(game.GamePlayer):
    """Represents a remote player.

    Attributes:
    """
    def __init__(self, server_address, port=PORT):
        super(RemotePlayer, self).__init__(local_human=False)

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((server_address, port))

        self.client_id = int(self.s.recv(1024)[0])
        print(f'Connected to {server_address} as client: {self.client_id}')

    def choose_color(self, state):
        """Returns whether to choose to play as Red.

        Args:
            state: GameState.
        """
        data = self.s.recv(1024)
        return data[0] == 1

    def get_move(self, state):
        """Returns a GameMove for the current color.

        Args:
            state: GameState to move in.
        """
        data = self.s.recv(1024)
        return game.GameMove.deserialize(data, state)

    def update_color_choice(self, choose_red):
        """Makes update to internal state given other players move.

        Args:
            choose_red: Whether the other player chose red.
        """
        self.s.send(bytes([1 if choose_red else 0]))

    def update_move(self, move):
        """Makes update to internal state given other players move.

        Args:
            move: Move made by other player.
        """
        self.s.send(move.serialize())


# Create and run a server that forwards messages from any client to all others.
# Server will also send connection index to client.
if __name__ == '__main__':

    connections = []

    def on_new_client(client_socket, connections, addr, num_clients):
        print(f'Connected to client {num_clients}: {addr}')
        client_socket.send(bytes([num_clients]))
        while True:
            msg = client_socket.recv(1024)
            for c in connections:
                if c != client_socket:
                    c.send(msg)
        client_socket.close()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.bind(('', PORT))
    s.listen()

    print(f'Waiting for connection on port {PORT}')

    num_clients = 0

    while True:
        c, addr = s.accept()
        connections.append(c)
        threading.Thread(target=on_new_client, args=(c, connections, addr, num_clients)).start()
        num_clients += 1

    s.close()
