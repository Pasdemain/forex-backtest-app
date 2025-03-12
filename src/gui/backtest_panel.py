# First find and replace the problematic line

# Update statistics labels
            self.total_trades_label.config(text=str(stats['total_entries']))
            self.win_rate_label.config(text=f"{stats['win_rate']:.1f}%")
            self.avg_duration_label.config(text="N/A hours")
            
            # Update graphs