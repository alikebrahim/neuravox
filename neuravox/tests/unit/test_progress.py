"""Unit tests for shared progress tracking module"""
import time
from unittest.mock import MagicMock, patch
import pytest
from rich.console import Console

from modules.shared.progress import UnifiedProgressTracker


class TestUnifiedProgressTracker:
    """Test UnifiedProgressTracker functionality"""
    
    def test_initialization(self):
        """Test progress tracker initialization"""
        tracker = UnifiedProgressTracker()
        
        assert isinstance(tracker.console, Console)
        assert tracker.tasks == {}
        assert tracker.start_time > 0
    
    def test_custom_console(self):
        """Test initialization with custom console"""
        custom_console = Console()
        tracker = UnifiedProgressTracker(console=custom_console)
        
        assert tracker.console is custom_console
    
    def test_add_task(self):
        """Test adding a new task"""
        tracker = UnifiedProgressTracker()
        
        # Mock the progress.add_task method
        with patch.object(tracker.progress, 'add_task', return_value='task_123'):
            task_id = tracker.add_task('test_task', 'Testing task', 100)
            
            # Verify task was added to progress
            tracker.progress.add_task.assert_called_once_with('Testing task', total=100)
            
            # Verify task was tracked internally
            assert 'test_task' in tracker.tasks
            assert tracker.tasks['test_task']['id'] == 'task_123'
            assert tracker.tasks['test_task']['total'] == 100
            assert tracker.tasks['test_task']['completed'] == 0
            assert tracker.tasks['test_task']['start_time'] > 0
    
    def test_update_task(self):
        """Test updating task progress"""
        tracker = UnifiedProgressTracker()
        
        # Mock progress methods
        with patch.object(tracker.progress, 'add_task', return_value='task_123'):
            with patch.object(tracker.progress, 'update') as mock_update:
                # Add a task
                tracker.add_task('test_task', 'Testing', 100)
                
                # Update progress
                tracker.update_task('test_task', advance=10)
                
                # Verify update was called
                mock_update.assert_called_with('task_123', advance=10)
                assert tracker.tasks['test_task']['completed'] == 10
                
                # Update with description
                tracker.update_task('test_task', advance=5, description='New description')
                
                # Verify both advance and description update
                assert mock_update.call_count == 3  # 2 for advance, 1 for description
                assert tracker.tasks['test_task']['completed'] == 15
    
    def test_update_nonexistent_task(self):
        """Test updating a task that doesn't exist"""
        tracker = UnifiedProgressTracker()
        
        # Should not raise error, just ignore
        tracker.update_task('nonexistent', advance=10)
    
    def test_finish_task(self):
        """Test finishing a task"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task', return_value='task_123'):
            with patch.object(tracker.progress, 'update') as mock_update:
                # Add a task
                tracker.add_task('test_task', 'Testing', 100)
                
                # Update partially
                tracker.update_task('test_task', advance=30)
                
                # Finish task
                tracker.finish_task('test_task')
                
                # Should advance by remaining amount (70)
                mock_update.assert_called_with('task_123', advance=70)
    
    def test_finish_completed_task(self):
        """Test finishing an already completed task"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task', return_value='task_123'):
            with patch.object(tracker.progress, 'update') as mock_update:
                # Add a task
                tracker.add_task('test_task', 'Testing', 50)
                
                # Complete the task
                tracker.update_task('test_task', advance=50)
                
                # Reset mock to check finish behavior
                mock_update.reset_mock()
                
                # Finish task (should do nothing as already complete)
                tracker.finish_task('test_task')
                
                # Should not call update as remaining is 0
                mock_update.assert_not_called()
    
    def test_finish_nonexistent_task(self):
        """Test finishing a task that doesn't exist"""
        tracker = UnifiedProgressTracker()
        
        # Should not raise error, just ignore
        tracker.finish_task('nonexistent')
    
    def test_context_manager(self):
        """Test using progress tracker as context manager"""
        tracker = UnifiedProgressTracker()
        
        # Mock the progress context manager methods
        tracker.progress.__enter__ = MagicMock(return_value=tracker.progress)
        tracker.progress.__exit__ = MagicMock(return_value=None)
        
        # Use as context manager
        with tracker as t:
            assert t is tracker
            tracker.progress.__enter__.assert_called_once()
        
        # Verify exit was called
        tracker.progress.__exit__.assert_called_once()
    
    def test_multiple_tasks(self):
        """Test managing multiple tasks simultaneously"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task', side_effect=['task_1', 'task_2', 'task_3']):
            with patch.object(tracker.progress, 'update'):
                # Add multiple tasks
                tracker.add_task('processing', 'Processing files', 10)
                tracker.add_task('transcribing', 'Transcribing audio', 20)
                tracker.add_task('saving', 'Saving results', 5)
                
                # Verify all tasks are tracked
                assert len(tracker.tasks) == 3
                assert 'processing' in tracker.tasks
                assert 'transcribing' in tracker.tasks
                assert 'saving' in tracker.tasks
                
                # Update different tasks
                tracker.update_task('processing', advance=5)
                tracker.update_task('transcribing', advance=10)
                tracker.update_task('saving', advance=2)
                
                # Verify progress
                assert tracker.tasks['processing']['completed'] == 5
                assert tracker.tasks['transcribing']['completed'] == 10
                assert tracker.tasks['saving']['completed'] == 2
    
    def test_task_timing(self):
        """Test that task timing is tracked correctly"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task', return_value='task_123'):
            # Record start time
            start_time = time.time()
            
            # Add task
            tracker.add_task('timed_task', 'Timing test', 100)
            
            # Task start time should be close to our start time
            task_start = tracker.tasks['timed_task']['start_time']
            assert abs(task_start - start_time) < 0.1  # Within 100ms
    
    def test_progress_description_formats(self):
        """Test various description formats"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task') as mock_add:
            # Test different description styles
            descriptions = [
                "Simple description",
                "Processing file: test.mp3",
                "Step 1/5: Analyzing audio",
                "🎵 Transcribing chunk 3 of 10"
            ]
            
            for i, desc in enumerate(descriptions):
                tracker.add_task(f'task_{i}', desc, 100)
                mock_add.assert_called_with(desc, total=100)
    
    def test_zero_total_task(self):
        """Test handling tasks with zero total"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task', return_value='task_123'):
            # Add task with zero total
            tracker.add_task('zero_task', 'Zero total task', 0)
            
            # Should handle gracefully
            assert tracker.tasks['zero_task']['total'] == 0
            assert tracker.tasks['zero_task']['completed'] == 0
            
            # Finishing should not cause issues
            with patch.object(tracker.progress, 'update') as mock_update:
                tracker.finish_task('zero_task')
                mock_update.assert_not_called()  # No update needed


class TestProgressIntegration:
    """Test progress tracker integration scenarios"""
    
    def test_pipeline_progress_simulation(self):
        """Simulate a typical pipeline progress flow"""
        tracker = UnifiedProgressTracker()
        
        with patch.object(tracker.progress, 'add_task', side_effect=['proc_id', 'trans_id']):
            with patch.object(tracker.progress, 'update') as mock_update:
                # Simulate audio processing
                tracker.add_task('processing', 'Processing audio.mp3', 100)
                
                # Simulate progress updates
                for i in range(10):
                    tracker.update_task('processing', advance=10)
                
                tracker.finish_task('processing')
                
                # Simulate transcription
                tracker.add_task('transcription', 'Transcribing 5 chunks', 5)
                
                for i in range(5):
                    tracker.update_task('transcription', advance=1, 
                                      description=f'Transcribing chunk {i+1}/5')
                
                tracker.finish_task('transcription')
                
                # Verify correct number of updates
                assert tracker.tasks['processing']['completed'] == 100
                assert tracker.tasks['transcription']['completed'] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])