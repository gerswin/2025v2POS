from rest_framework import serializers
from django.utils import timezone
from .models import SalesReport, OccupancyAnalysis, ReportSchedule


class SalesReportSerializer(serializers.ModelSerializer):
    """Serializer for SalesReport model."""
    
    duration_display = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_failed = serializers.ReadOnlyField()
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = SalesReport
        fields = [
            'id',
            'name',
            'report_type',
            'filters',
            'total_transactions',
            'total_revenue',
            'total_tickets',
            'average_ticket_price',
            'period_start',
            'period_end',
            'duration_display',
            'status',
            'is_completed',
            'is_failed',
            'generated_by',
            'generated_by_name',
            'export_formats',
            'detailed_data',
            'created_at',
            'completed_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'total_transactions',
            'total_revenue',
            'total_tickets',
            'average_ticket_price',
            'status',
            'generated_by',
            'completed_at',
            'created_at',
            'updated_at'
        ]
    
    def validate(self, data):
        """Validate report data."""
        if data.get('period_start') and data.get('period_end'):
            if data['period_start'] >= data['period_end']:
                raise serializers.ValidationError({
                    'period_end': 'End date must be after start date'
                })
        
        return data


class SalesReportCreateSerializer(serializers.Serializer):
    """Serializer for creating sales reports."""
    
    name = serializers.CharField(max_length=255)
    report_type = serializers.ChoiceField(choices=SalesReport.ReportType.choices)
    
    # Filter options
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    event_id = serializers.UUIDField(required=False)
    zone_id = serializers.UUIDField(required=False)
    operator_id = serializers.UUIDField(required=False)
    
    # Export options
    export_formats = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    
    def validate(self, data):
        """Validate report creation data."""
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        # Validate export formats
        valid_formats = ['json', 'csv', 'pdf']
        for format_type in data.get('export_formats', []):
            if format_type not in valid_formats:
                raise serializers.ValidationError({
                    'export_formats': f'Invalid export format: {format_type}. Valid formats: {valid_formats}'
                })
        
        return data
    
    def create(self, validated_data):
        """Create a new sales report."""
        # Extract filter data
        filters = {}
        filter_fields = ['start_date', 'end_date', 'event_id', 'zone_id', 'operator_id']
        for field in filter_fields:
            if field in validated_data:
                filters[field] = validated_data.pop(field)
        
        # Get tenant from context
        tenant = self.context['request'].user.tenant
        
        # Create report
        report = SalesReport.objects.create_sales_report(
            tenant=tenant,
            filters=filters,
            generated_by=self.context['request'].user,
            **validated_data
        )
        
        return report


class OccupancyAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for OccupancyAnalysis model."""
    
    available_capacity = serializers.ReadOnlyField()
    occupancy_status = serializers.ReadOnlyField()
    performance_rating = serializers.ReadOnlyField()
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    
    class Meta:
        model = OccupancyAnalysis
        fields = [
            'id',
            'name',
            'analysis_type',
            'event',
            'event_name',
            'zone',
            'zone_name',
            'total_capacity',
            'sold_tickets',
            'available_capacity',
            'fill_rate',
            'occupancy_status',
            'sales_velocity',
            'performance_rating',
            'heat_map_data',
            'performance_metrics',
            'analysis_start',
            'analysis_end',
            'generated_by',
            'generated_by_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'total_capacity',
            'sold_tickets',
            'fill_rate',
            'sales_velocity',
            'heat_map_data',
            'performance_metrics',
            'generated_by',
            'created_at',
            'updated_at'
        ]


class OccupancyAnalysisCreateSerializer(serializers.Serializer):
    """Serializer for creating occupancy analyses."""
    
    name = serializers.CharField(max_length=255)
    analysis_type = serializers.ChoiceField(choices=OccupancyAnalysis.AnalysisType.choices)
    event_id = serializers.UUIDField(required=False)
    zone_id = serializers.UUIDField(required=False)
    analysis_start = serializers.DateTimeField(required=False)
    analysis_end = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        """Validate analysis creation data."""
        if data.get('analysis_start') and data.get('analysis_end'):
            if data['analysis_start'] >= data['analysis_end']:
                raise serializers.ValidationError({
                    'analysis_end': 'End date must be after start date'
                })
        
        # Validate that either event or zone is provided for specific analysis types
        if data['analysis_type'] == OccupancyAnalysis.AnalysisType.ZONE:
            if not data.get('zone_id'):
                raise serializers.ValidationError({
                    'zone_id': 'Zone ID is required for zone analysis'
                })
        elif data['analysis_type'] == OccupancyAnalysis.AnalysisType.EVENT:
            if not data.get('event_id'):
                raise serializers.ValidationError({
                    'event_id': 'Event ID is required for event analysis'
                })
        
        return data
    
    def create(self, validated_data):
        """Create a new occupancy analysis."""
        from venezuelan_pos.apps.events.models import Event
        from venezuelan_pos.apps.zones.models import Zone
        
        # Get tenant from context
        tenant = self.context['request'].user.tenant
        
        # Get event and zone objects if provided
        event = None
        zone = None
        
        if validated_data.get('event_id'):
            try:
                event = Event.objects.get(id=validated_data['event_id'], tenant=tenant)
            except Event.DoesNotExist:
                raise serializers.ValidationError({'event_id': 'Event not found'})
        
        if validated_data.get('zone_id'):
            try:
                zone = Zone.objects.get(id=validated_data['zone_id'], tenant=tenant)
            except Zone.DoesNotExist:
                raise serializers.ValidationError({'zone_id': 'Zone not found'})
        
        # Remove IDs from validated_data
        validated_data.pop('event_id', None)
        validated_data.pop('zone_id', None)
        
        # Create analysis
        analysis = OccupancyAnalysis.objects.create_occupancy_analysis(
            tenant=tenant,
            event=event,
            zone=zone,
            generated_by=self.context['request'].user,
            **validated_data
        )
        
        return analysis


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for ReportSchedule model."""
    
    is_active = serializers.ReadOnlyField()
    is_due = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id',
            'name',
            'description',
            'report_type',
            'report_filters',
            'frequency',
            'next_run',
            'last_run',
            'status',
            'is_active',
            'is_due',
            'email_recipients',
            'export_formats',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'last_run',
            'created_by',
            'created_at',
            'updated_at'
        ]
    
    def validate_next_run(self, value):
        """Validate next run time."""
        if value <= timezone.now():
            raise serializers.ValidationError('Next run must be in the future')
        return value
    
    def validate_email_recipients(self, value):
        """Validate email recipients."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Email recipients must be a list')
        
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for email in value:
            if not re.match(email_pattern, email):
                raise serializers.ValidationError(f'Invalid email address: {email}')
        
        return value
    
    def validate_export_formats(self, value):
        """Validate export formats."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Export formats must be a list')
        
        valid_formats = ['json', 'csv', 'pdf']
        for format_type in value:
            if format_type not in valid_formats:
                raise serializers.ValidationError(f'Invalid export format: {format_type}')
        
        return value


class ReportExportSerializer(serializers.Serializer):
    """Serializer for report export requests."""
    
    format = serializers.ChoiceField(
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('pdf', 'PDF')
        ]
    )
    include_details = serializers.BooleanField(default=False)
    
    def validate_format(self, value):
        """Validate export format."""
        valid_formats = ['json', 'csv', 'pdf']
        if value not in valid_formats:
            raise serializers.ValidationError(f'Invalid format. Valid formats: {valid_formats}')
        return value


class HeatMapDataSerializer(serializers.Serializer):
    """Serializer for heat map data."""
    
    zone_id = serializers.UUIDField()
    event_id = serializers.UUIDField(required=False)
    
    def validate_zone_id(self, value):
        """Validate zone exists and belongs to tenant."""
        from venezuelan_pos.apps.zones.models import Zone
        
        tenant = self.context['request'].user.tenant
        
        try:
            zone = Zone.objects.get(id=value, tenant=tenant)
        except Zone.DoesNotExist:
            raise serializers.ValidationError('Zone not found')
        
        return value
    
    def validate_event_id(self, value):
        """Validate event exists and belongs to tenant."""
        if value is None:
            return value
        
        from venezuelan_pos.apps.events.models import Event
        
        tenant = self.context['request'].user.tenant
        
        try:
            event = Event.objects.get(id=value, tenant=tenant)
        except Event.DoesNotExist:
            raise serializers.ValidationError('Event not found')
        
        return value


class ZoneMetricsSerializer(serializers.Serializer):
    """Serializer for zone performance metrics requests."""
    
    zone_id = serializers.UUIDField()
    event_id = serializers.UUIDField(required=False)
    period_days = serializers.IntegerField(default=30, min_value=1, max_value=365)
    
    def validate_zone_id(self, value):
        """Validate zone exists and belongs to tenant."""
        from venezuelan_pos.apps.zones.models import Zone
        
        tenant = self.context['request'].user.tenant
        
        try:
            zone = Zone.objects.get(id=value, tenant=tenant)
        except Zone.DoesNotExist:
            raise serializers.ValidationError('Zone not found')
        
        return value
    
    def validate_event_id(self, value):
        """Validate event exists and belongs to tenant."""
        if value is None:
            return value
        
        from venezuelan_pos.apps.events.models import Event
        
        tenant = self.context['request'].user.tenant
        
        try:
            event = Event.objects.get(id=value, tenant=tenant)
        except Event.DoesNotExist:
            raise serializers.ValidationError('Event not found')
        
        return value


class OccupancyTrendsSerializer(serializers.Serializer):
    """Serializer for occupancy trends requests."""
    
    zone_id = serializers.UUIDField()
    days = serializers.IntegerField(default=30, min_value=1, max_value=365)
    
    def validate_zone_id(self, value):
        """Validate zone exists and belongs to tenant."""
        from venezuelan_pos.apps.zones.models import Zone
        
        tenant = self.context['request'].user.tenant
        
        try:
            zone = Zone.objects.get(id=value, tenant=tenant)
        except Zone.DoesNotExist:
            raise serializers.ValidationError('Zone not found')
        
        return value


class ComparativeAnalysisSerializer(serializers.Serializer):
    """Serializer for comparative analysis requests."""
    
    zone_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=2,
        max_length=10
    )
    event_id = serializers.UUIDField(required=False)
    
    def validate_zone_ids(self, value):
        """Validate zones exist and belong to tenant."""
        from venezuelan_pos.apps.zones.models import Zone
        
        tenant = self.context['request'].user.tenant
        
        zones = Zone.objects.filter(id__in=value, tenant=tenant)
        
        if zones.count() != len(value):
            raise serializers.ValidationError('One or more zones not found')
        
        return value
    
    def validate_event_id(self, value):
        """Validate event exists and belongs to tenant."""
        if value is None:
            return value
        
        from venezuelan_pos.apps.events.models import Event
        
        tenant = self.context['request'].user.tenant
        
        try:
            event = Event.objects.get(id=value, tenant=tenant)
        except Event.DoesNotExist:
            raise serializers.ValidationError('Event not found')
        
        return value