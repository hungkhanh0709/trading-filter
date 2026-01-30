"""
Sentiment Analyzer - Phân tích tâm lý thị trường (20 điểm)
"""


class SentimentAnalyzer:
    """Phân tích tâm lý thị trường - 20 điểm"""
    
    def __init__(self, insider_data, shareholders_data):
        """
        Initialize sentiment analyzer
        
        Args:
            insider_data: Insider deals dataframe
            shareholders_data: Shareholders dataframe
        """
        self.insider = insider_data
        self.shareholders = shareholders_data
    
    def get_total_score(self):
        """
        Tổng điểm Sentiment - 20 điểm
        
        Returns:
            dict: Score breakdown
        """
        insider_score = 0
        insider_reason = "Không có dữ liệu"
        
        # Insider deals - 10 điểm
        if self.insider is not None and len(self.insider) > 0:
            # Kiểm tra giao dịch 3 tháng gần nhất
            # Giả sử có cột 'dealMethod' hoặc 'type' để phân biệt mua/bán
            # Nếu không có, skip phần này
            insider_reason = "Có dữ liệu insider nhưng cần phân tích thêm"
            insider_score = 5  # Default moderate score
        
        # Foreign ownership - 5 điểm
        foreign_score = 0
        foreign_reason = "Không có dữ liệu"
        
        if self.shareholders is not None and len(self.shareholders) > 0:
            # Tìm sở hữu nước ngoài
            # Cần check column names thực tế
            foreign_reason = "Có dữ liệu cổ đông"
            foreign_score = 3  # Default
        
        # News - 5 điểm (placeholder)
        news_score = 3
        news_reason = "Neutral (cần tích hợp news API)"
        
        return {
            'total': insider_score + foreign_score + news_score,
            'max': 20,
            'breakdown': {
                'insider': {'score': insider_score, 'max': 10, 'reason': insider_reason},
                'foreign': {'score': foreign_score, 'max': 5, 'reason': foreign_reason},
                'news': {'score': news_score, 'max': 5, 'reason': news_reason}
            }
        }
