from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from .models import SalesReport, OccupancyAnalysis


class ReportService:
    """Service class for report generation and analytics."""
    
    @staticmethod
    def generate_sales_report_data(tenant, filters=None):
        """
        Generate comprehensive sales report data with detailed breakdowns.
        """
        from venezuelan_pos.apps.sales.models import Transaction, TransactionItem
        from venezuelan_pos.apps.events.models import Event
        from venezuelan_pos.apps.zones.models import Zone
        
        if filters is None:
            filters = {}
        
        # Base queryset for completed transactions
        transactions_qs = Transaction.objects.filter(
            tenant=tenant,
            status=Transaction.Status.COMPLETED
        )
        
        # Apply filters
        if filters.get('start_date'):
            transactions_qs = transactions_qs.filter(completed_at__gte=filters['start_date'])
        if filters.get('end_date'):
            transactions_qs = transactions_qs.filter(completed_at__lte=filters['end_date'])
        if filters.get('event_id'):
            transactions_qs = transactions_qs.filter(event_id=filters['event_id'])
        if filters.get('operator_id'):
            transactions_qs = transactions_qs.filter(created_by_id=filters['operator_id'])
        
        # Base aggregations
        base_stats = transactions_qs.aggregate(
            total_transactions=Count('id'),
            total_revenue=Sum('total_amount'),
            total_subtotal=Sum('subtotal_amount'),
            total_tax=Sum('tax_amount'),
            average_transaction_value=Avg('total_amount')
        )
        
        # Handle None values
        for key, value in base_stats.items():
            if value is None:
                base_stats[key] = 0 if 'total_' in key or 'average_' in key else 0
        
        # Get total tickets sold
        items_qs = TransactionItem.objects.filter(
            transaction__in=transactions_qs
        )
        
        if filters.get('zone_id'):
            items_qs = items_qs.filter(zone_id=filters['zone_id'])
        
        ticket_stats = items_qs.aggregate(
            total_tickets=Sum('quantity'),
            average_ticket_price=Avg('total_price')
        )
        
        base_stats.update({
            'total_tickets': ticket_stats['total_tickets'] or 0,
            'average_ticket_price': ticket_stats['average_ticket_price'] or Decimal('0.00')
        })
        
        # Detailed breakdowns
        detailed_data = {
            'base_statistics': base_stats,
            'breakdowns': {}
        }
        
        # Event breakdown
        if not filters.get('event_id'):  # Only if not filtering by specific event
            event_breakdown = []
            events = Event.objects.filter(
                tenant=tenant,
                transactions__in=transactions_qs
            ).distinct()
            
            for event in events:
                event_transactions = transactions_qs.filter(event=event)
                event_stats = event_transactions.aggregate(
                    transactions=Count('id'),
                    revenue=Sum('total_amount'),
                    tickets=Sum('items__quantity')
                )
                
                event_breakdown.append({
                    'event_id': str(event.id),
                    'event_name': event.name,
                    'transactions': event_stats['transactions'] or 0,
                    'revenue': float(event_stats['revenue'] or 0),
                    'tickets': event_stats['tickets'] or 0
                })
            
            detailed_data['breakdowns']['by_event'] = event_breakdown
        
        # Zone breakdown
        if not filters.get('zone_id'):  # Only if not filtering by specific zone
            zone_breakdown = []
            zones = Zone.objects.filter(
                tenant=tenant,
                transaction_items__transaction__in=transactions_qs
            ).distinct()
            
            for zone in zones:
                zone_items = items_qs.filter(zone=zone)
                zone_stats = zone_items.aggregate(
                    tickets=Sum('quantity'),
                    revenue=Sum('total_price')
                )
                
                zone_breakdown.append({
                    'zone_id': str(zone.id),
                    'zone_name': zone.name,
                    'event_name': zone.event.name,
                    'tickets': zone_stats['tickets'] or 0,
                    'revenue': float(zone_stats['revenue'] or 0),
                    'capacity': zone.capacity,
                    'fill_rate': (zone_stats['tickets'] or 0) / zone.capacity * 100 if zone.capacity > 0 else 0
                })
            
            detailed_data['breakdowns']['by_zone'] = zone_breakdown
        
        # Daily breakdown (for date range reports)
        if filters.get('start_date') and filters.get('end_date'):
            daily_breakdown = []
            current_date = filters['start_date'].date()
            end_date = filters['end_date'].date()
            
            while current_date <= end_date:
                day_transactions = transactions_qs.filter(
                    completed_at__date=current_date
                )
                day_stats = day_transactions.aggregate(
                    transactions=Count('id'),
                    revenue=Sum('total_amount'),
                    tickets=Sum('items__quantity')
                )
                
                daily_breakdown.append({
                    'date': current_date.isoformat(),
                    'transactions': day_stats['transactions'] or 0,
                    'revenue': float(day_stats['revenue'] or 0),
                    'tickets': day_stats['tickets'] or 0
                })
                
                current_date += timedelta(days=1)
            
            detailed_data['breakdowns']['by_day'] = daily_breakdown
        
        # Payment method breakdown
        payment_breakdown = []
        from venezuelan_pos.apps.payments.models import Payment
        
        payments = Payment.objects.filter(
            transaction__in=transactions_qs,
            status='completed'
        ).values('payment_method__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        )
        
        for payment in payments:
            payment_breakdown.append({
                'method': payment['payment_method__name'] or 'Unknown',
                'count': payment['count'],
                'amount': float(payment['total_amount'] or 0)
            })
        
        detailed_data['breakdowns']['by_payment_method'] = payment_breakdown
        
        return detailed_data
    
    @staticmethod
    def generate_occupancy_heat_map(zone, event=None):
        """
        Generate detailed heat map data for a numbered zone.
        """
        from venezuelan_pos.apps.zones.models import Seat
        from venezuelan_pos.apps.sales.models import TransactionItem
        
        if zone.zone_type != zone.ZoneType.NUMBERED:
            return {
                'error': 'Heat maps are only available for numbered zones'
            }
        
        # Get all seats in the zone
        seats = Seat.objects.filter(zone=zone).order_by('row_number', 'seat_number')
        
        # Get transaction items for this zone
        items_qs = TransactionItem.objects.filter(
            zone=zone,
            transaction__status='completed'
        )
        
        if event:
            items_qs = items_qs.filter(transaction__event=event)
        
        # Build heat map structure
        heat_map = {
            'zone_id': str(zone.id),
            'zone_name': zone.name,
            'event_id': str(event.id) if event else None,
            'event_name': event.name if event else None,
            'rows': zone.rows,
            'total_capacity': zone.capacity,
            'grid': {},
            'popularity_metrics': {}
        }
        
        # Initialize grid with all seats
        for row in range(1, zone.rows + 1):
            seats_in_row = zone.get_seats_for_row(row)
            heat_map['grid'][row] = {}
            
            for seat_num in range(1, seats_in_row + 1):
                heat_map['grid'][row][seat_num] = {
                    'status': 'available',
                    'price': float(zone.base_price),
                    'sales_count': 0,
                    'total_revenue': 0.0,
                    'last_sold': None,
                    'popularity_score': 0.0,
                    'demand_level': 'low'
                }
        
        # Update with actual seat data and calculate popularity
        row_popularity = {}
        max_sales_count = 0
        
        for seat in seats:
            if seat.row_number in heat_map['grid'] and seat.seat_number in heat_map['grid'][seat.row_number]:
                # Get sales data for this seat
                seat_items = items_qs.filter(seat=seat)
                sales_count = seat_items.count()
                total_revenue = sum(float(item.total_price) for item in seat_items)
                
                # Track max sales for normalization
                max_sales_count = max(max_sales_count, sales_count)
                
                # Get last sale date
                last_sale = seat_items.order_by('-transaction__completed_at').first()
                last_sold = last_sale.transaction.completed_at.isoformat() if last_sale else None
                
                # Calculate popularity score (0-100)
                popularity_score = (sales_count / max(max_sales_count, 1)) * 100
                
                # Determine demand level
                if popularity_score >= 80:
                    demand_level = 'very_high'
                elif popularity_score >= 60:
                    demand_level = 'high'
                elif popularity_score >= 40:
                    demand_level = 'medium'
                elif popularity_score >= 20:
                    demand_level = 'low'
                else:
                    demand_level = 'very_low'
                
                heat_map['grid'][seat.row_number][seat.seat_number] = {
                    'status': seat.status,
                    'price': float(seat.calculated_price),
                    'sales_count': sales_count,
                    'total_revenue': total_revenue,
                    'last_sold': last_sold,
                    'popularity_score': round(popularity_score, 2),
                    'demand_level': demand_level
                }
                
                # Track row popularity
                if seat.row_number not in row_popularity:
                    row_popularity[seat.row_number] = {
                        'sales_count': 0,
                        'total_revenue': 0.0,
                        'seat_count': 0
                    }
                
                row_popularity[seat.row_number]['sales_count'] += sales_count
                row_popularity[seat.row_number]['total_revenue'] += total_revenue
                row_popularity[seat.row_number]['seat_count'] += 1
        
        # Calculate row-level popularity metrics
        for row_num, row_data in row_popularity.items():
            if row_data['seat_count'] > 0:
                avg_sales_per_seat = row_data['sales_count'] / row_data['seat_count']
                avg_revenue_per_seat = row_data['total_revenue'] / row_data['seat_count']
                fill_rate = (row_data['sales_count'] / row_data['seat_count']) * 100
                
                heat_map['popularity_metrics'][f'row_{row_num}'] = {
                    'average_sales_per_seat': round(avg_sales_per_seat, 2),
                    'average_revenue_per_seat': round(avg_revenue_per_seat, 2),
                    'fill_rate': round(fill_rate, 2),
                    'total_sales': row_data['sales_count'],
                    'total_revenue': round(row_data['total_revenue'], 2)
                }
        
        # Calculate summary statistics
        total_sold = sum(
            seat_data['sales_count']
            for row_data in heat_map['grid'].values()
            for seat_data in row_data.values()
        )
        
        total_revenue = sum(
            seat_data['total_revenue']
            for row_data in heat_map['grid'].values()
            for seat_data in row_data.values()
        )
        
        # Calculate zone-level popularity distribution
        demand_distribution = {'very_high': 0, 'high': 0, 'medium': 0, 'low': 0, 'very_low': 0}
        for row_data in heat_map['grid'].values():
            for seat_data in row_data.values():
                demand_distribution[seat_data['demand_level']] += 1
        
        heat_map['summary'] = {
            'total_sold': total_sold,
            'total_revenue': total_revenue,
            'fill_rate': (total_sold / zone.capacity * 100) if zone.capacity > 0 else 0,
            'average_price': (total_revenue / total_sold) if total_sold > 0 else 0,
            'demand_distribution': demand_distribution,
            'most_popular_row': max(row_popularity.keys(), 
                                  key=lambda r: row_popularity[r]['sales_count']) if row_popularity else None,
            'least_popular_row': min(row_popularity.keys(), 
                                   key=lambda r: row_popularity[r]['sales_count']) if row_popularity else None
        }
        
        return heat_map
    
    @staticmethod
    def calculate_zone_performance_metrics(zone, event=None, period_days=30):
        """
        Calculate comprehensive performance metrics for a zone.
        """
        from venezuelan_pos.apps.sales.models import TransactionItem
        from datetime import datetime, timedelta
        
        # Get sales data for the zone
        items_qs = TransactionItem.objects.filter(
            zone=zone,
            transaction__status='completed'
        )
        
        if event:
            items_qs = items_qs.filter(transaction__event=event)
        
        # Calculate period-based metrics
        period_start = timezone.now() - timedelta(days=period_days)
        recent_items = items_qs.filter(transaction__completed_at__gte=period_start)
        
        # Basic metrics
        total_sold = items_qs.aggregate(total=Sum('quantity'))['total'] or 0
        recent_sold = recent_items.aggregate(total=Sum('quantity'))['total'] or 0
        total_revenue = items_qs.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
        recent_revenue = recent_items.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
        
        # Calculate rates
        fill_rate = (total_sold / zone.capacity * 100) if zone.capacity > 0 else 0
        sales_velocity = recent_sold / period_days if period_days > 0 else 0
        revenue_velocity = float(recent_revenue) / period_days if period_days > 0 else 0
        
        # Calculate average ticket price
        avg_ticket_price = float(total_revenue) / total_sold if total_sold > 0 else 0
        recent_avg_price = float(recent_revenue) / recent_sold if recent_sold > 0 else 0
        
        # Calculate trends (compare with previous period)
        previous_period_start = period_start - timedelta(days=period_days)
        previous_items = items_qs.filter(
            transaction__completed_at__gte=previous_period_start,
            transaction__completed_at__lt=period_start
        )
        
        previous_sold = previous_items.aggregate(total=Sum('quantity'))['total'] or 0
        previous_revenue = previous_items.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
        
        # Calculate growth rates
        sales_growth = ((recent_sold - previous_sold) / previous_sold * 100) if previous_sold > 0 else 0
        revenue_growth = ((float(recent_revenue) - float(previous_revenue)) / float(previous_revenue) * 100) if previous_revenue > 0 else 0
        
        # Calculate daily sales pattern (last 7 days)
        daily_sales = []
        for i in range(7):
            day_start = timezone.now() - timedelta(days=i+1)
            day_end = day_start + timedelta(days=1)
            day_sales = items_qs.filter(
                transaction__completed_at__gte=day_start,
                transaction__completed_at__lt=day_end
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            daily_sales.append({
                'date': day_start.date().isoformat(),
                'sales': day_sales
            })
        
        # Calculate peak sales times (if we have hourly data)
        hourly_distribution = {}
        for item in recent_items.select_related('transaction'):
            hour = item.transaction.completed_at.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + item.quantity
        
        peak_hour = max(hourly_distribution.keys(), key=lambda h: hourly_distribution[h]) if hourly_distribution else None
        
        # Performance ranking factors
        performance_score = 0
        
        # Fill rate score (0-40 points)
        if fill_rate >= 95:
            performance_score += 40
        elif fill_rate >= 85:
            performance_score += 35
        elif fill_rate >= 75:
            performance_score += 30
        elif fill_rate >= 60:
            performance_score += 25
        elif fill_rate >= 50:
            performance_score += 20
        elif fill_rate >= 35:
            performance_score += 15
        elif fill_rate >= 25:
            performance_score += 10
        elif fill_rate >= 10:
            performance_score += 5
        
        # Sales velocity score (0-30 points)
        if sales_velocity >= 15:
            performance_score += 30
        elif sales_velocity >= 10:
            performance_score += 25
        elif sales_velocity >= 7:
            performance_score += 20
        elif sales_velocity >= 5:
            performance_score += 15
        elif sales_velocity >= 3:
            performance_score += 10
        elif sales_velocity >= 1:
            performance_score += 5
        
        # Growth trend score (0-20 points)
        if sales_growth >= 25:
            performance_score += 20
        elif sales_growth >= 15:
            performance_score += 15
        elif sales_growth >= 5:
            performance_score += 10
        elif sales_growth >= 0:
            performance_score += 5
        elif sales_growth >= -10:
            performance_score += 2
        
        # Revenue efficiency score (0-10 points)
        base_price_float = float(zone.base_price)
        if avg_ticket_price >= base_price_float * 1.2:
            performance_score += 10
        elif avg_ticket_price >= base_price_float * 1.1:
            performance_score += 7
        elif avg_ticket_price >= base_price_float:
            performance_score += 5
        elif avg_ticket_price >= base_price_float * 0.9:
            performance_score += 2
        
        # Determine performance grade and category
        if performance_score >= 85:
            performance_grade = 'A+'
            performance_category = 'Outstanding'
        elif performance_score >= 80:
            performance_grade = 'A'
            performance_category = 'Excellent'
        elif performance_score >= 70:
            performance_grade = 'B+'
            performance_category = 'Very Good'
        elif performance_score >= 60:
            performance_grade = 'B'
            performance_category = 'Good'
        elif performance_score >= 50:
            performance_grade = 'C+'
            performance_category = 'Above Average'
        elif performance_score >= 40:
            performance_grade = 'C'
            performance_category = 'Average'
        elif performance_score >= 30:
            performance_grade = 'D+'
            performance_category = 'Below Average'
        elif performance_score >= 20:
            performance_grade = 'D'
            performance_category = 'Poor'
        else:
            performance_grade = 'F'
            performance_category = 'Very Poor'
        
        # Calculate efficiency metrics
        capacity_utilization = (total_sold / zone.capacity) if zone.capacity > 0 else 0
        revenue_per_capacity = float(total_revenue) / zone.capacity if zone.capacity > 0 else 0
        
        return {
            'zone_id': str(zone.id),
            'zone_name': zone.name,
            'zone_type': zone.zone_type,
            'capacity': zone.capacity,
            'total_sold': total_sold,
            'recent_sold': recent_sold,
            'available_capacity': zone.capacity - total_sold,
            'total_revenue': float(total_revenue),
            'recent_revenue': float(recent_revenue),
            'fill_rate': round(fill_rate, 2),
            'capacity_utilization': round(capacity_utilization * 100, 2),
            'sales_velocity': round(sales_velocity, 2),
            'revenue_velocity': round(revenue_velocity, 2),
            'revenue_per_capacity': round(revenue_per_capacity, 2),
            'avg_ticket_price': round(avg_ticket_price, 2),
            'recent_avg_price': round(recent_avg_price, 2),
            'sales_growth': round(sales_growth, 2),
            'revenue_growth': round(revenue_growth, 2),
            'performance_score': performance_score,
            'performance_grade': performance_grade,
            'performance_category': performance_category,
            'daily_sales_pattern': daily_sales,
            'peak_sales_hour': peak_hour,
            'hourly_distribution': hourly_distribution,
            'period_days': period_days,
            'analysis_date': timezone.now().isoformat()
        }
    
    @staticmethod
    def generate_comparative_analysis(zones, event=None):
        """
        Generate comparative analysis across multiple zones.
        """
        analysis_data = []
        
        for zone in zones:
            metrics = ReportService.calculate_zone_performance_metrics(zone, event)
            analysis_data.append(metrics)
        
        # Sort by performance score
        analysis_data.sort(key=lambda x: x['performance_score'], reverse=True)
        
        # Add rankings
        for i, data in enumerate(analysis_data, 1):
            data['rank'] = i
        
        # Calculate summary statistics
        total_capacity = sum(data['capacity'] for data in analysis_data)
        total_sold = sum(data['total_sold'] for data in analysis_data)
        total_revenue = sum(data['total_revenue'] for data in analysis_data)
        
        summary = {
            'total_zones': len(analysis_data),
            'total_capacity': total_capacity,
            'total_sold': total_sold,
            'total_revenue': total_revenue,
            'overall_fill_rate': (total_sold / total_capacity * 100) if total_capacity > 0 else 0,
            'average_performance_score': sum(data['performance_score'] for data in analysis_data) / len(analysis_data) if analysis_data else 0
        }
        
        return {
            'summary': summary,
            'zones': analysis_data
        }
    
    @staticmethod
    def generate_zone_popularity_ranking(event=None, tenant=None, limit=None):
        """
        Generate zone popularity ranking based on multiple metrics.
        """
        from venezuelan_pos.apps.zones.models import Zone
        
        # Get zones to analyze
        zones_qs = Zone.objects.filter(status=Zone.Status.ACTIVE)
        
        if tenant:
            zones_qs = zones_qs.filter(tenant=tenant)
        if event:
            zones_qs = zones_qs.filter(event=event)
        
        ranking_data = []
        
        for zone in zones_qs:
            metrics = ReportService.calculate_zone_performance_metrics(zone, event)
            
            # Calculate popularity score based on multiple factors
            popularity_score = 0
            
            # Fill rate weight (40%)
            popularity_score += metrics['fill_rate'] * 0.4
            
            # Sales velocity weight (30%)
            # Normalize velocity (assume 5 tickets/day is good performance)
            velocity_normalized = min(metrics['sales_velocity'] / 5.0, 1.0) * 100
            popularity_score += velocity_normalized * 0.3
            
            # Revenue efficiency weight (20%)
            if zone.base_price > 0:
                base_price_float = float(zone.base_price)
                price_efficiency = (metrics['avg_ticket_price'] / base_price_float) * 100
                price_efficiency = min(price_efficiency, 150)  # Cap at 150%
                popularity_score += price_efficiency * 0.2
            
            # Growth trend weight (10%)
            growth_score = max(0, min(metrics['sales_growth'] + 50, 100))  # Normalize -50 to +50 as 0 to 100
            popularity_score += growth_score * 0.1
            
            ranking_data.append({
                'zone_id': str(zone.id),
                'zone_name': zone.name,
                'zone_type': zone.zone_type,
                'event_name': zone.event.name if zone.event else None,
                'popularity_score': round(popularity_score, 2),
                'fill_rate': metrics['fill_rate'],
                'sales_velocity': metrics['sales_velocity'],
                'revenue_velocity': metrics['revenue_velocity'],
                'avg_ticket_price': metrics['avg_ticket_price'],
                'total_revenue': metrics['total_revenue'],
                'capacity': metrics['capacity'],
                'total_sold': metrics['total_sold'],
                'performance_grade': metrics['performance_grade'],
                'performance_category': metrics['performance_category'],
                'sales_growth': metrics['sales_growth'],
                'revenue_growth': metrics['revenue_growth']
            })
        
        # Sort by popularity score
        ranking_data.sort(key=lambda x: x['popularity_score'], reverse=True)
        
        # Add rank numbers
        for i, zone_data in enumerate(ranking_data, 1):
            zone_data['rank'] = i
        
        # Apply limit if specified
        if limit:
            ranking_data = ranking_data[:limit]
        
        # Calculate summary statistics
        total_zones = len(ranking_data)
        avg_popularity = sum(z['popularity_score'] for z in ranking_data) / total_zones if total_zones > 0 else 0
        avg_fill_rate = sum(z['fill_rate'] for z in ranking_data) / total_zones if total_zones > 0 else 0
        total_capacity = sum(z['capacity'] for z in ranking_data)
        total_sold = sum(z['total_sold'] for z in ranking_data)
        total_revenue = sum(z['total_revenue'] for z in ranking_data)
        
        return {
            'ranking': ranking_data,
            'summary': {
                'total_zones': total_zones,
                'average_popularity_score': round(avg_popularity, 2),
                'average_fill_rate': round(avg_fill_rate, 2),
                'total_capacity': total_capacity,
                'total_sold': total_sold,
                'total_revenue': round(total_revenue, 2),
                'overall_fill_rate': round((total_sold / total_capacity * 100) if total_capacity > 0 else 0, 2)
            },
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def generate_occupancy_trends(zone, days=30):
        """
        Generate occupancy trends over time for a specific zone.
        """
        from venezuelan_pos.apps.sales.models import TransactionItem
        from datetime import datetime, timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get daily sales data
        daily_data = []
        current_date = start_date.date()
        
        while current_date <= end_date.date():
            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            
            day_sales = TransactionItem.objects.filter(
                zone=zone,
                transaction__status='completed',
                transaction__completed_at__gte=day_start,
                transaction__completed_at__lt=day_end
            ).aggregate(
                tickets_sold=Sum('quantity'),
                revenue=Sum('total_price')
            )
            
            tickets_sold = day_sales['tickets_sold'] or 0
            revenue = float(day_sales['revenue'] or 0)
            fill_rate = (tickets_sold / zone.capacity * 100) if zone.capacity > 0 else 0
            
            daily_data.append({
                'date': current_date.isoformat(),
                'tickets_sold': tickets_sold,
                'revenue': revenue,
                'fill_rate': round(fill_rate, 2),
                'cumulative_sold': sum(d['tickets_sold'] for d in daily_data) + tickets_sold
            })
            
            current_date += timedelta(days=1)
        
        # Calculate trend metrics
        if len(daily_data) >= 2:
            recent_avg = sum(d['tickets_sold'] for d in daily_data[-7:]) / min(7, len(daily_data))
            early_avg = sum(d['tickets_sold'] for d in daily_data[:7]) / min(7, len(daily_data))
            trend_direction = 'increasing' if recent_avg > early_avg else 'decreasing' if recent_avg < early_avg else 'stable'
            trend_percentage = ((recent_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0
        else:
            trend_direction = 'insufficient_data'
            trend_percentage = 0
        
        return {
            'zone_id': str(zone.id),
            'zone_name': zone.name,
            'period_days': days,
            'daily_data': daily_data,
            'trend_analysis': {
                'direction': trend_direction,
                'percentage_change': round(trend_percentage, 2),
                'recent_average': round(recent_avg, 2) if len(daily_data) >= 2 else 0,
                'early_average': round(early_avg, 2) if len(daily_data) >= 2 else 0
            },
            'summary': {
                'total_tickets_sold': sum(d['tickets_sold'] for d in daily_data),
                'total_revenue': sum(d['revenue'] for d in daily_data),
                'peak_day': max(daily_data, key=lambda d: d['tickets_sold']) if daily_data else None,
                'average_daily_sales': sum(d['tickets_sold'] for d in daily_data) / len(daily_data) if daily_data else 0
            }
        }