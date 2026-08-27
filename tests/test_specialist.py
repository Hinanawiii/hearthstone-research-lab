import unittest

from cardlab.engine import Game
from cardlab.specialist.features import ACTION_SIZE, STATE_SIZE, encode_action, encode_state


class FeatureTests(unittest.TestCase):
    def test_feature_shapes_are_stable(self) -> None:
        game = Game(seed=40)
        observation = game.observation(game.state.active_player)
        action = game.legal_actions()[0]
        self.assertEqual(len(encode_state(observation)), STATE_SIZE)
        self.assertEqual(len(encode_action(observation, action)), ACTION_SIZE)


if __name__ == "__main__":
    unittest.main()

