from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Topic
from .services import due_reviews, recommend


@login_required
def recommendations(request):
    topic = request.GET.get("topic", "")
    platform = request.GET.get("platform", "")
    mode = request.GET.get("mode", "learn")
    if mode not in {"learn", "weak", "challenge", "review"}:
        mode = "learn"
    return render(
        request,
        "recommendations.html",
        {
            "recommendations": recommend(request.user, topic, platform, mode),
            "reviews": due_reviews(request.user),
            "topics": Topic.objects.order_by("name"),
            "platforms": ["codeforces", "atcoder", "codechef", "cses", "leetcode"],
            "selected_topic": topic,
            "selected_platform": platform,
            "mode": mode,
        },
    )
