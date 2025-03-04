from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.db.models import Q
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Price, Registrator, TeamMember
from .forms import CompaniesSortForm, ContactForm
from .tasks import send_join_team_mail
from .serializers import PriceSerializer, ContactSerializer


SORT_FIELD_NAMES = {
    'CN': 'registrator__name',
    'CI': 'registrator__city',
    'RE': 'price_reg',
    'PR': 'price_prolong',
    'PE': 'price_change',

}


class RegistratorList(generics.ListAPIView):
    queryset = Price.objects.all()
    serializer_class = PriceSerializer
    search_fields = ['registrator__website', 'registrator__name']
    ordering_fields = [
        'id',
        'registrator__name',
        'registrator__city',
        'registrator__id',
        'parse__id',
        'created_at',
        'price_reg',
        'price_prolong',
        'price_change'
        'reg_status',
        'prolong_status',
        'change_status',
    ]


class RegistratorDetail(generics.RetrieveAPIView):
    serializer_class = PriceSerializer
    queryset = Price.objects.all()


class ContactView(generics.GenericAPIView):
    serializer_class = ContactSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            name = serializer.validated_data.get('name')
            contact = serializer.validated_data.get('contact')
            speciality = serializer.validated_data.get('speciality')
            message = serializer.validated_data.get('message')

            send_join_team_mail.delay(name, contact, speciality, message)

            return Response({'message': 'email sent'})

        return Response(serializer.errors, status=400)


def registrator_list(request):
    if request.method == "POST":
        form = CompaniesSortForm(request.POST)
        if form.is_valid():
            sort_by = (form.cleaned_data['reverse_order']
                       + SORT_FIELD_NAMES.get(
                        form.cleaned_data['sort_by'], 'name'))
            search = form.cleaned_data['search']

    else:
        form = CompaniesSortForm()
        sort_by = 'id'
        search = ''

    if search:
        companies = Price.objects.filter(
            Q(registrator__name__icontains=search) |
            Q(registrator__website__icontains=search)
            )
    else:
        companies = Price.objects.filter()

    companies = companies.order_by('registrator_id', '-parse__id', '-created_at').distinct('registrator_id')

    sort_by_lst = []
    if 'price_reg' in sort_by:
        sort_by_lst = ['-reg_status', sort_by]
    elif 'price_prolong' in sort_by:
        sort_by_lst = ['-prolong_status', sort_by]
    elif 'price_change' in sort_by:
        sort_by_lst = ['-change_status', sort_by]
    else:
        sort_by_lst = [sort_by]

    companies = Price.objects.filter(id__in=companies).order_by(*sort_by_lst)

    return render(request, 'registrator-list.html', {'companies': companies, 'form': form})


def registrator_details(request, id):
    try:
        registrator = Registrator.objects.get(id=id)
        prices = Price.objects.filter(registrator=registrator)
    except Price.DoesNotExist:
        return HttpResponseNotFound(f"Компания с идентификатором {id} в базе не найдена.")
    return render(request, 'registrator-details.html', {'prices': prices, 'registrator': registrator})


def about(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Логика обработки из формы обратной связи
            # отправка сообщения по почте админу.
            # TODO
            name = request.POST.get("name")
            contact = request.POST.get("contact")
            speciality = request.POST.get("speciality")
            message = request.POST.get("message")
            send_join_team_mail.delay(name, contact, speciality, message)

    else:
        form = ContactForm()

    team_members = TeamMember.objects.all()

    return render(request, 'about-us.html', {'contact_form': form, 'team_members': team_members})


def project_view(request):
    return render(request, 'project.html')
