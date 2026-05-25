from django.http import JsonResponse
from django.views.decorators.http import require_GET

from reports.master_data.models import (
    Project,
    ProjectArea,
    ProjectPhase,
    Category,
    Subcategory,
    MasterCode,
)
from reports.services.weather_service import fetch_weather


@require_GET
def master_code_builder_options(request):
    phase_id = request.GET.get("phase_id")
    category_id = request.GET.get("category_id")
    subcategory_id = request.GET.get("subcategory_id")

    qs = MasterCode.objects.filter(
        is_active=True,
        document_type__isnull=True,
    ).select_related("project_phase", "category", "subcategory")

    if phase_id:
        qs = qs.filter(project_phase_id=phase_id)

    if category_id:
        qs = qs.filter(category_id=category_id)

    if subcategory_id:
        qs = qs.filter(subcategory_id=subcategory_id)

    data = {
        "project_phases": list(
            ProjectPhase.objects.filter(is_active=True)
            .order_by("display_order", "phase_code")
            .values("id", "phase_code", "phase_name")
        ),
        "categories": list(
            Category.objects.filter(is_active=True)
            .order_by("symbol")
            .values("id", "symbol", "description")
        ),
        "subcategories": list(
            Subcategory.objects.filter(is_active=True)
            .order_by("category__symbol", "symbol")
            .values("id", "category_id", "symbol", "description")
        ),
        "codes": list(
            qs.values(
                "id",
                "code",
                "description",
                "project_phase_id",
                "category_id",
                "subcategory_id",
            )
        ),
    }

    return JsonResponse(data)


@require_GET
def project_areas_options(request):
    project_id = request.GET.get("project_id")

    if not project_id:
        return JsonResponse({"success": False, "error": "Project ID is required."}, status=400)

    areas = ProjectArea.objects.filter(
        project_id=project_id,
        is_active=True,
    ).order_by("sort_order", "code")

    return JsonResponse(
        {
            "success": True,
            "areas": list(
                areas.values("id", "code", "name", "area_type")
            ),
        }
    )


@require_GET
def fetch_project_weather(request):
    project_id = request.GET.get("project_id")

    if not project_id:
        return JsonResponse(
            {"success": False, "error": "Project ID is required."},
            status=400,
        )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found."},
            status=404,
        )

    if project.latitude is None or project.longitude is None:
        return JsonResponse(
            {"success": False, "error": "Project latitude and longitude are missing."},
            status=400,
        )

    try:
        weather = fetch_weather(project.latitude, project.longitude)
        temperature = weather.get("temperature")

        return JsonResponse(
            {
                "success": True,
                "temperature": round(temperature) if temperature is not None else "",
                "weather_condition": weather.get("weather_condition", ""),
                "weather_code": weather.get("weather_code", ""),
                "weather_source": "api_confirmed",
                "weather_confirmed": True,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )