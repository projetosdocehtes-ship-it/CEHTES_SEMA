# from django.test import TestCase
# from django.urls import reverse

# from .forms import MinutaForm
# from .models import Minuta, Variable


# class ModelTestCase(TestCase):
#     def test_minuta_creation(self):
#         minuta = Minuta.objects.create(title="Test Minuta", content="Hello, {name}!")
#         assert str(minuta) == minuta.title

#     def test_variable_creation(self):
#         minuta = Minuta.objects.create(title="Test Minuta", content="Hello, {name}!")
#         variable = Variable.objects.create(name="name", minuta=minuta)
#         assert str(variable) == variable.name


# class MinutaViewTestCase(TestCase):
#     def setUp(self):
#         self.minuta = Minuta.objects.create(title="Test Minuta", content="Hello, {name}!")

#     def test_minuta_list_view(self):
#         response = self.client.get(reverse("minuta_list"))
#         assert response.status_code == 200
#         self.assertContains(response, self.minuta.title)

#     def test_minuta_detail_view(self):
#         response = self.client.get(reverse("minuta_detail", args=[self.minuta.id]))
#         assert response.status_code == 200
#         self.assertContains(response, self.minuta.content)

#     def test_minuta_create_view(self):
#         response = self.client.get(reverse("minuta_create"))
#         assert response.status_code == 200

#     def test_minuta_update_view(self):
#         response = self.client.get(reverse("minuta_edit", args=[self.minuta.id]))
#         assert response.status_code == 200
#         self.assertContains(response, self.minuta.content)

#     def test_minuta_delete_view(self):
#         response = self.client.get(reverse("minuta_delete", args=[self.minuta.id]))
#         assert response.status_code == 200
#         self.assertContains(response, self.minuta.title)


# class MinutaFormTestCase(TestCase):
#     def test_minuta_form_valid(self):
#         form = MinutaForm(data={"title": "Test Minuta", "content": "Hello, {name}!"})
#         assert form.is_valid()

#     def test_minuta_form_invalid(self):
#         form = MinutaForm(data={"title": "", "content": ""})
#         assert not form.is_valid()
