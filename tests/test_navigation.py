import pytest
import numpy as np
import torch
from unittest.mock import patch, MagicMock
from simulations.equations import force_vector, total_thrust, acceleration  # Assuming available
from ai.navigation import MIMONetwork, simulate_navigation, train_demo_model, plot_trajectory

# Mock equations if not imported
if 'force_vector' not in globals():
    def force_vector(*args):
        return np.array([1.0, 0.0, 0.0])
    
    def total_thrust(*args):
        return 1000.0
    
    def acceleration(*args):
        return np.array([0.1, 0.0, 0.0])

@pytest.fixture
def sample_model():
    return MIMONetwork(input_size=9, hidden_size=32, output_size=6)

def test_mimo_network_init(sample_model):
    assert isinstance(sample_model, torch.nn.Module)
    assert sample_model.fc1.in_features == 9
    assert sample_model.fc1.out_features == 32
    assert sample_model.fc3.out_features == 6

def test_mimo_network_forward(sample_model):
    input_tensor = torch.randn(1, 9)  # Batch size 1
    output = sample_model(input_tensor)
    assert output.shape == (1, 6)
    assert torch.all(output >= -1) and torch.all(output <= 1)  # tanh output

def test_simulate_navigation_basic(sample_model):
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([10.0, 0.0, 0.0])
    
    trajectory = simulate_navigation(sample_model, start_pos, start_vel, target_pos)
    assert len(trajectory) > 1
    assert np.allclose(trajectory[0], start_pos)
    # Check if moving towards target (loose check)
    final_pos = trajectory[-1]
    assert np.linalg.norm(final_pos - target_pos) < np.linalg.norm(start_pos - target_pos) or np.linalg.norm(final_pos - target_pos) < 1.0

def test_simulate_navigation_with_obstacles(sample_model):
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([100.0, 0.0, 0.0])
    obstacles = [np.array([50.0, 0.0, 0.0])]
    
    trajectory = simulate_navigation(sample_model, start_pos, start_vel, target_pos, obstacles)
    assert len(trajectory) > 1
    # Check avoidance: trajectory should deviate in y or z
    traj = np.array(trajectory)
    assert np.any(np.abs(traj[:, 1]) > 0) or np.any(np.abs(traj[:, 2]) > 0)

def test_simulate_navigation_reaches_target(sample_model):
    # Force quick reach by setting small distance
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([0.5, 0.0, 0.0])  # Close target
    
    with patch('builtins.print') as mock_print:
        trajectory = simulate_navigation(sample_model, start_pos, start_vel, target_pos)
        mock_print.assert_called_with(pytest regex="Reached target at step \d+")

def test_train_demo_model():
    model = train_demo_model()
    assert isinstance(model, MIMONetwork)
    # Check if training ran without errors (basic)

@patch('matplotlib.pyplot.show')
def test_plot_trajectory(mock_show):
    trajectory = [np.array([0,0,0]), np.array([1,1,1]), np.array([2,2,2])]
    plot_trajectory(trajectory)
    mock_show.assert_called_once()

