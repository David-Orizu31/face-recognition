import os
import json
import tempfile
from PIL import Image
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import Person, FaceRecord
from .utils import extract_embedding, compress_image_from_memory, find_matches


def home(request):
    total_persons = Person.objects.count()
    total_faces   = FaceRecord.objects.count()
    return render(request, 'recognition/home.html', {
        'total_persons': total_persons,
        'total_faces'  : total_faces,
    })


def enroll_face(request):
    return render(request, 'recognition/enroll.html')


@require_POST
def enroll_face_ajax(request):
    """AJAX endpoint for face enrollment — returns JSON"""
    name       = request.POST.get('name', '').strip()
    image_file = request.FILES.get('image')

    if not name:
        return JsonResponse({'success': False, 'error': 'Please enter a name.'})
    if not image_file:
        return JsonResponse({'success': False, 'error': 'Please upload an image.'})

    suffix = os.path.splitext(image_file.name)[1] or '.jpg'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in image_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        # Stage 1 — Extracting features
        embedding = extract_embedding(tmp_path)

        # Stage 2 — Compressing image
        pil_image     = Image.open(tmp_path)
        filename      = f"person_{name.replace(' ', '_')}_{FaceRecord.objects.count() + 1}.jpg"
        relative_path = f"faces/thumbnails/{filename}"
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        compress_image_from_memory(pil_image, absolute_path)

        # Stage 3 — Saving to database
        person, created = Person.objects.get_or_create(name=name)
        face_record = FaceRecord.objects.create(
            person     = person,
            image      = relative_path,
            embedding  = embedding,
            model_used = 'ArcFace',
        )

        return JsonResponse({
            'success'   : True,
            'message'   : f'Face enrolled successfully for {name}!',
            'person'    : name,
            'face_id'   : face_record.pk,
            'is_new'    : created,
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'Face detection failed: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def search_face(request):
    return render(request, 'recognition/search.html')


@require_POST
def search_face_ajax(request):
    """AJAX endpoint for face search — returns JSON"""
    image_file = request.FILES.get('image')

    if not image_file:
        return JsonResponse({'success': False, 'error': 'Please upload an image.'})

    suffix = os.path.splitext(image_file.name)[1] or '.jpg'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in image_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        matches = find_matches(tmp_path)
        return JsonResponse({
            'success': True,
            'count'  : len(matches),
            'matches': matches,
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'Face detection failed: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def enrolled_list(request):
    persons = Person.objects.prefetch_related('faces').all()
    return render(request, 'recognition/enrolled_list.html', {'persons': persons})


def delete_face(request, face_id):
    try:
        record = FaceRecord.objects.get(pk=face_id)
        person = record.person

        # ── Delete the image file from media folder ──────────────
        if record.image:
            image_path = os.path.join(settings.MEDIA_ROOT, str(record.image))
            if os.path.exists(image_path):
                os.remove(image_path)

        # ── Delete the face record from database ─────────────────
        record.delete()

        # ── Delete the person if they have no remaining faces ────
        if person.faces.count() == 0:
            person.delete()
            messages.success(request, f'Face record and person "{person.name}" deleted successfully.')
        else:
            remaining = person.faces.count()
            messages.success(request, f'Face record deleted. {person.name} still has {remaining} face record(s).')

    except FaceRecord.DoesNotExist:
        messages.error(request, 'Face record not found.')

    return redirect('enrolled_list')