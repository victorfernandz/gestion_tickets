from django.test import TestCase, Client
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone

from .models import (
    Departamento, Rol, Usuario, Categoria, Casos,
    Ticket, Comentario, ArchivoAdjunto, TokenRestablecimiento
)
from .views import get_emails_jefes


# ═══════════════════════════════════════════════════════════════
#  FIXTURES: helpers para crear objetos reutilizables
# ═══════════════════════════════════════════════════════════════

def crear_departamento(descripcion='TI'):
    return Departamento.objects.create(descripcion=descripcion)

def crear_rol(descripcion='USUARIO'):
    return Rol.objects.create(descripcion=descripcion)

def crear_usuario(usuario='jdoe', nombre='Juan', apellido='Doe',
                  email='juan@test.com', departamento=None, rol=None,
                  contrasena='password123'):
    if departamento is None:
        departamento = crear_departamento()
    if rol is None:
        rol = crear_rol()
    return Usuario.objects.create(
        usuario=usuario,
        nombre=nombre,
        apellido=apellido,
        email=email,
        departamento=departamento,
        rol=rol,
        contrasena=make_password(contrasena),
    )

def crear_ticket(usuario, categoria=None, caso=None, descripcion='Falla en sistema',
                 prioridad=2, estado=1):
    if categoria is None:
        categoria = Categoria.objects.create(descripcion='Software')
    if caso is None:
        caso = Casos.objects.create(descripcion='Error de acceso', categoria=categoria)
    return Ticket.objects.create(
        usuario=usuario,
        creador=usuario,
        categoria=categoria,
        tipoCaso=caso,
        descripcion=descripcion,
        prioridad=prioridad,
        estado=estado,
    )


# ═══════════════════════════════════════════════════════════════
#  1. TESTS DE MODELOS
# ═══════════════════════════════════════════════════════════════

class DepartamentoModelTest(TestCase):
    def test_str(self):
        depto = Departamento.objects.create(descripcion='Recursos Humanos')
        self.assertEqual(str(depto), 'Recursos Humanos')

    def test_descripcion_unica(self):
        Departamento.objects.create(descripcion='Finanzas')
        with self.assertRaises(Exception):
            Departamento.objects.create(descripcion='Finanzas')


class RolModelTest(TestCase):
    def test_str(self):
        rol = Rol.objects.create(descripcion='ADMIN')
        self.assertEqual(str(rol), 'ADMIN')


class UsuarioModelTest(TestCase):
    def setUp(self):
        self.depto = crear_departamento('TI')
        self.rol = crear_rol('USUARIO')

    def test_str(self):
        u = crear_usuario(departamento=self.depto, rol=self.rol)
        self.assertEqual(str(u), 'Juan Doe (jdoe)')

    def test_usuario_unico(self):
        crear_usuario(usuario='admin1', departamento=self.depto, rol=self.rol)
        with self.assertRaises(Exception):
            crear_usuario(usuario='admin1', departamento=self.depto, rol=self.rol)

    def test_necesita_cambiar_contrasena_default_false(self):
        u = crear_usuario(departamento=self.depto, rol=self.rol)
        self.assertFalse(u.necesita_cambiar_contrasena)


class TicketModelTest(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()

    def test_str(self):
        ticket = crear_ticket(self.usuario)
        self.assertIn('Ticket', str(ticket))
        self.assertIn(str(ticket.id), str(ticket))

    def test_estado_default_abierto(self):
        ticket = crear_ticket(self.usuario)
        self.assertEqual(ticket.estado, 1)
        self.assertEqual(ticket.get_estado_display(), 'Abierto')

    def test_prioridad_display(self):
        ticket = crear_ticket(self.usuario, prioridad=4)
        self.assertEqual(ticket.get_prioridad_display(), 'Muy Alto')

    def test_creador_se_guarda(self):
        ticket = crear_ticket(self.usuario)
        self.assertEqual(ticket.creador, self.usuario)

    def test_admin_asignado_null_por_defecto(self):
        ticket = crear_ticket(self.usuario)
        self.assertIsNone(ticket.admin_asignado)


class ComentarioModelTest(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.ticket = crear_ticket(self.usuario)

    def test_crear_comentario(self):
        comentario = Comentario.objects.create(
            ticket=self.ticket,
            usuario=self.usuario,
            texto='Este es un comentario de prueba.'
        )
        self.assertEqual(comentario.ticket, self.ticket)
        self.assertEqual(comentario.texto, 'Este es un comentario de prueba.')

    def test_str_comentario(self):
        comentario = Comentario.objects.create(
            ticket=self.ticket, usuario=self.usuario, texto='Test'
        )
        self.assertIn(str(self.ticket.id), str(comentario))


class TokenRestablecimientoTest(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()

    def test_token_activo_recien_creado(self):
        token = TokenRestablecimiento.objects.create(
            usuario=self.usuario,
            token=get_random_string(50)
        )
        self.assertTrue(token.esta_activo())

    def test_token_inactivo_si_usado(self):
        token = TokenRestablecimiento.objects.create(
            usuario=self.usuario,
            token=get_random_string(50),
            usado=True
        )
        self.assertFalse(token.esta_activo())

    def test_token_inactivo_si_expirado(self):
        token = TokenRestablecimiento.objects.create(
            usuario=self.usuario,
            token=get_random_string(50)
        )
        TokenRestablecimiento.objects.filter(pk=token.pk).update(
            fecha_creacion=timezone.now() - timedelta(hours=25)
        )
        token.refresh_from_db()
        self.assertFalse(token.esta_activo())


# ═══════════════════════════════════════════════════════════════
#  2. TESTS DEL HELPER get_emails_jefes
# ═══════════════════════════════════════════════════════════════

class GetEmailsJefesTest(TestCase):
    def setUp(self):
        self.depto_ti = crear_departamento('TI')
        self.depto_rrhh = crear_departamento('RRHH')
        self.rol_usuario = crear_rol('USUARIO')
        self.rol_jefe = Rol.objects.create(descripcion='JEFE')

        self.usuario = crear_usuario(
            usuario='u1', email='u1@test.com',
            departamento=self.depto_ti, rol=self.rol_usuario
        )
        self.jefe_ti = crear_usuario(
            usuario='j1', email='jefe_ti@test.com',
            departamento=self.depto_ti, rol=self.rol_jefe
        )
        self.jefe_rrhh = crear_usuario(
            usuario='j2', email='jefe_rrhh@test.com',
            departamento=self.depto_rrhh, rol=self.rol_jefe
        )

    def test_retorna_email_jefe_del_departamento(self):
        emails = get_emails_jefes(self.usuario)
        self.assertIn('jefe_ti@test.com', emails)

    def test_no_retorna_jefe_de_otro_departamento(self):
        emails = get_emails_jefes(self.usuario)
        self.assertNotIn('jefe_rrhh@test.com', emails)

    def test_excluye_al_usuario_si_el_mismo_es_jefe(self):
        emails = get_emails_jefes(self.jefe_ti)
        self.assertNotIn('jefe_ti@test.com', emails)

    def test_retorna_lista_vacia_si_no_hay_jefes(self):
        self.jefe_ti.delete()
        emails = get_emails_jefes(self.usuario)
        self.assertEqual(emails, [])

    def test_multiples_jefes_en_mismo_departamento(self):
        crear_usuario(
            usuario='j3', email='jefe_ti2@test.com',
            departamento=self.depto_ti, rol=self.rol_jefe
        )
        emails = get_emails_jefes(self.usuario)
        self.assertIn('jefe_ti@test.com', emails)
        self.assertIn('jefe_ti2@test.com', emails)
        self.assertEqual(len(emails), 2)


# ═══════════════════════════════════════════════════════════════
#  3. TESTS DE VISTA — Login / Logout
# ═══════════════════════════════════════════════════════════════

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('login')
        self.usuario = crear_usuario(usuario='testuser', contrasena='clave123')

    def test_get_muestra_formulario(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_login_exitoso_redirige_a_home(self):
        response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'clave123',
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_contrasena_incorrecta(self):
        response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'incorrecta',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('user_id', self.client.session)

    def test_login_usuario_inexistente(self):
        response = self.client.post(self.url, {
            'username': 'noexiste',
            'password': 'clave123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('user_id', self.client.session)

    def test_login_guarda_user_id_en_sesion(self):
        self.client.post(self.url, {'username': 'testuser', 'password': 'clave123'})
        self.assertEqual(self.client.session['user_id'], self.usuario.id)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario(usuario='testuser', contrasena='clave123')
        self.client.post(reverse('login'), {'username': 'testuser', 'password': 'clave123'})

    def test_logout_limpia_sesion(self):
        self.assertIn('user_id', self.client.session)
        self.client.get(reverse('logout'))
        self.assertNotIn('user_id', self.client.session)

    def test_logout_redirige_a_login(self):
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))


# ═══════════════════════════════════════════════════════════════
#  4. TESTS DE VISTA — Home / Dashboard
# ═══════════════════════════════════════════════════════════════

class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol_usuario = crear_rol('USUARIO')
        self.rol_admin = Rol.objects.create(descripcion='ADMIN')
        self.rol_jefe = Rol.objects.create(descripcion='JEFE')
        self.depto = crear_departamento('TI')

    def _login(self, usuario):
        session = self.client.session
        session['user_id'] = usuario.id
        session.save()

    def test_sin_sesion_redirige_a_login(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('login'))

    def test_usuario_normal_ve_home(self):
        u = crear_usuario(departamento=self.depto, rol=self.rol_usuario)
        self._login(u)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('mis_abiertos', response.context)

    def test_admin_ve_metricas_de_admin(self):
        u = crear_usuario(usuario='admin1', email='a@test.com',
                          departamento=self.depto, rol=self.rol_admin)
        self._login(u)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_abiertos', response.context)
        self.assertIn('sin_asignar', response.context)

    def test_jefe_ve_metricas_de_departamento(self):
        u = crear_usuario(usuario='jefe1', email='j@test.com',
                          departamento=self.depto, rol=self.rol_jefe)
        self._login(u)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('depto_abiertos', response.context)

    def test_conteo_tickets_usuario(self):
        u = crear_usuario(departamento=self.depto, rol=self.rol_usuario)
        crear_ticket(u, estado=1)
        crear_ticket(u, estado=1)
        crear_ticket(u, estado=4)
        self._login(u)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['mis_abiertos'], 2)
        self.assertEqual(response.context['mis_cerrados'], 1)


# ═══════════════════════════════════════════════════════════════
#  5. TESTS DE VISTA — Crear Ticket
# ═══════════════════════════════════════════════════════════════

class CrearTicketViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol = crear_rol('USUARIO')
        self.depto = crear_departamento('TI')
        self.usuario = crear_usuario(departamento=self.depto, rol=self.rol)
        self.categoria = Categoria.objects.create(descripcion='Hardware')
        self.caso = Casos.objects.create(descripcion='PC no enciende', categoria=self.categoria)

        session = self.client.session
        session['user_id'] = self.usuario.id
        session.save()

    def test_sin_sesion_redirige_a_login(self):
        response = Client().get(reverse('crear_ticket'))
        self.assertRedirects(response, reverse('login'))

    def test_get_muestra_formulario(self):
        response = self.client.get(reverse('crear_ticket'))
        self.assertEqual(response.status_code, 200)

    @patch('tickets.views.enviar_correo_admin.delay')
    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_post_valido_crea_ticket(self, mock_usuario, mock_admin):
        self.client.post(reverse('crear_ticket'), {
            'categoria': self.categoria.id,
            'tipoCaso': self.caso.id,
            'descripcion': 'El equipo no enciende desde esta mañana.',
            'prioridad': 2,
        })
        self.assertEqual(Ticket.objects.count(), 1)
        ticket = Ticket.objects.first()
        self.assertEqual(ticket.descripcion, 'El equipo no enciende desde esta mañana.')
        self.assertEqual(ticket.estado, 1)

    @patch('tickets.views.enviar_correo_admin.delay')
    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_post_valido_redirige_a_listar(self, mock_usuario, mock_admin):
        response = self.client.post(reverse('crear_ticket'), {
            'categoria': self.categoria.id,
            'tipoCaso': self.caso.id,
            'descripcion': 'Descripción de prueba.',
            'prioridad': 1,
        })
        self.assertRedirects(response, reverse('listar_tickets'))

    @patch('tickets.views.enviar_correo_admin.delay')
    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_post_valido_envia_correos(self, mock_usuario, mock_admin):
        self.client.post(reverse('crear_ticket'), {
            'categoria': self.categoria.id,
            'tipoCaso': self.caso.id,
            'descripcion': 'Descripción de prueba.',
            'prioridad': 2,
        })
        self.assertTrue(mock_admin.called)
        self.assertTrue(mock_usuario.called)

    def test_post_sin_descripcion_no_crea_ticket(self):
        self.client.post(reverse('crear_ticket'), {
            'categoria': self.categoria.id,
            'tipoCaso': self.caso.id,
            'descripcion': '',
            'prioridad': 1,
        })
        self.assertEqual(Ticket.objects.count(), 0)

    def test_ajax_retorna_casos_por_categoria(self):
        response = self.client.get(
            reverse('crear_ticket'),
            {'categoria_id': self.categoria.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('casos', data)
        self.assertEqual(len(data['casos']), 1)
        self.assertEqual(data['casos'][0]['descripcion'], 'PC no enciende')


# ═══════════════════════════════════════════════════════════════
#  6. TESTS DE VISTA — Listar Tickets
# ═══════════════════════════════════════════════════════════════

class ListarTicketsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol_usuario = crear_rol('USUARIO')
        self.rol_admin = Rol.objects.create(descripcion='ADMIN')
        self.depto = crear_departamento('TI')
        self.usuario = crear_usuario(usuario='u1', email='u1@test.com',
                                     departamento=self.depto, rol=self.rol_usuario)
        self.otro = crear_usuario(usuario='u2', email='u2@test.com',
                                  departamento=self.depto, rol=self.rol_usuario)
        self.admin = crear_usuario(usuario='adm', email='adm@test.com',
                                   departamento=self.depto, rol=self.rol_admin)
        crear_ticket(self.usuario)
        crear_ticket(self.usuario)
        crear_ticket(self.otro)

    def _login(self, usuario):
        session = self.client.session
        session['user_id'] = usuario.id
        session.save()

    def test_sin_sesion_redirige_a_login(self):
        response = self.client.get(reverse('listar_tickets'))
        self.assertRedirects(response, reverse('login'))

    def test_usuario_ve_solo_sus_tickets(self):
        self._login(self.usuario)
        response = self.client.get(reverse('listar_tickets'))
        self.assertEqual(response.status_code, 200)
        for t in response.context['tickets']:
            self.assertEqual(t.usuario, self.usuario)

    def test_admin_ve_todos_los_tickets(self):
        self._login(self.admin)
        response = self.client.get(reverse('listar_tickets'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tickets'].paginator.count, 3)


# ═══════════════════════════════════════════════════════════════
#  7. TESTS DE VISTA — Administrar Tickets
# ═══════════════════════════════════════════════════════════════

class AdministrarTicketsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol_usuario = crear_rol('USUARIO')
        self.rol_admin = Rol.objects.create(descripcion='ADMIN')
        self.depto = crear_departamento('TI')
        self.usuario = crear_usuario(usuario='u1', email='u1@test.com',
                                     departamento=self.depto, rol=self.rol_usuario)
        self.admin = crear_usuario(usuario='adm', email='adm@test.com',
                                   departamento=self.depto, rol=self.rol_admin)

    def _login(self, usuario):
        session = self.client.session
        session['user_id'] = usuario.id
        session.save()

    def test_sin_sesion_redirige_a_login(self):
        response = self.client.get(reverse('administrar_tickets'))
        self.assertRedirects(response, reverse('login'))

    def test_usuario_normal_no_puede_acceder(self):
        self._login(self.usuario)
        response = self.client.get(reverse('administrar_tickets'))
        self.assertRedirects(response, reverse('home'))

    def test_admin_puede_acceder(self):
        self._login(self.admin)
        response = self.client.get(reverse('administrar_tickets'))
        self.assertEqual(response.status_code, 200)


# ═══════════════════════════════════════════════════════════════
#  8. TESTS DE VISTA — Seguimiento de Ticket
# ═══════════════════════════════════════════════════════════════

class SeguimientoTicketViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol = crear_rol('USUARIO')
        self.depto = crear_departamento('TI')
        self.usuario = crear_usuario(usuario='u1', email='u1@test.com',
                                     departamento=self.depto, rol=self.rol)
        self.otro = crear_usuario(usuario='u2', email='u2@test.com',
                                  departamento=self.depto, rol=self.rol)
        self.ticket = crear_ticket(self.usuario)

    def _login(self, usuario):
        session = self.client.session
        session['user_id'] = usuario.id
        session.save()

    def test_sin_sesion_redirige_a_login(self):
        response = self.client.get(reverse('seguimiento_ticket', args=[self.ticket.id]))
        self.assertRedirects(response, reverse('login'))

    def test_usuario_puede_ver_su_ticket(self):
        self._login(self.usuario)
        response = self.client.get(reverse('seguimiento_ticket', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 200)

    def test_otro_usuario_no_puede_ver_ticket_ajeno(self):
        self._login(self.otro)
        response = self.client.get(reverse('seguimiento_ticket', args=[self.ticket.id]))
        self.assertRedirects(response, reverse('home'))

    @patch('tickets.views.enviar_correo_admin.delay')
    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_agregar_comentario(self, mock_usuario, mock_admin):
        self._login(self.usuario)
        self.client.post(
            reverse('seguimiento_ticket', args=[self.ticket.id]),
            {'form_type': 'comentario', 'comentario': 'Mi comentario de prueba.'}
        )
        self.assertEqual(Comentario.objects.filter(ticket=self.ticket).count(), 1)
        self.assertEqual(Comentario.objects.get(ticket=self.ticket).texto,
                         'Mi comentario de prueba.')

    @patch('tickets.views.enviar_correo_admin.delay')
    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_comentario_vacio_no_se_guarda(self, mock_usuario, mock_admin):
        self._login(self.usuario)
        self.client.post(
            reverse('seguimiento_ticket', args=[self.ticket.id]),
            {'form_type': 'comentario', 'comentario': ''}
        )
        self.assertEqual(Comentario.objects.filter(ticket=self.ticket).count(), 0)


# ═══════════════════════════════════════════════════════════════
#  9. TESTS DE RESTABLECIMIENTO DE CONTRASEÑA
# ═══════════════════════════════════════════════════════════════

class RestablecerContrasenaViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol = crear_rol('USUARIO')
        self.depto = crear_departamento('TI')
        self.usuario = crear_usuario(
            usuario='u1', email='u1@altamiragroup.com.py',
            departamento=self.depto, rol=self.rol
        )

    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_solicitar_reset_con_email_valido(self, mock_correo):
        self.client.post(
            reverse('solicitar_restablecer_contrasena'),
            {'email': 'u1@altamiragroup.com.py'}
        )
        self.assertTrue(TokenRestablecimiento.objects.filter(usuario=self.usuario).exists())
        self.assertTrue(mock_correo.called)

    @patch('tickets.views.enviar_correo_usuario.delay')
    def test_solicitar_reset_email_inexistente_no_crea_token(self, mock_correo):
        self.client.post(
            reverse('solicitar_restablecer_contrasena'),
            {'email': 'noexiste@test.com'}
        )
        self.assertFalse(TokenRestablecimiento.objects.exists())

    def test_token_valido_muestra_formulario_reset(self):
        TokenRestablecimiento.objects.create(
            usuario=self.usuario, token='token-valido-test'
        )
        response = self.client.get(
            reverse('restablecer_contrasena', args=['token-valido-test'])
        )
        self.assertEqual(response.status_code, 200)

    def test_token_invalido_redirige(self):
        response = self.client.get(
            reverse('restablecer_contrasena', args=['token-inexistente'])
        )
        self.assertRedirects(response, reverse('login'))
