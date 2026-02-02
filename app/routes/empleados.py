from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Trabajador, Rol, Horario, Empresa
from app.forms import TrabajadorForm
from sqlalchemy.orm import joinedload

# Definimos el Blueprint para empleados
empleados_bp = Blueprint('empleados', __name__)

@empleados_bp.route('/empleados', methods=['GET', 'POST'])
@login_required
def listar_empleados():
    empresa_seleccionada_id = session.get('contexto_empresa')
    if empresa_seleccionada_id == 0: empresa_seleccionada_id = None

    if empresa_seleccionada_id:
        # Mantenemos la carga optimizada para evitar que salgan vacíos
        empleados = Trabajador.query.options(
            joinedload(Trabajador.rol),
            joinedload(Trabajador.horario)
        ).filter_by(idEmpresa=empresa_seleccionada_id).all()
        empresa_obj = Empresa.query.get(empresa_seleccionada_id)
    else:
        empleados = Trabajador.query.filter_by(idEmpresa=None).all()
        empresa_obj = None

    return render_template('empleados.html', empleados=empleados, empresa_actual=empresa_obj)

@empleados_bp.route('/empleados/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_empleado():
    form = TrabajadorForm()
    # Mantenemos el filtro para no mostrar roles de administración
    roles_permitidos = Rol.query.filter(Rol.nombre_rol.notin_(['Administrador', 'Superadministrador'])).all()
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]
    form.horario_id.choices = [(h.id_horario, h.nombre_horario) for h in Horario.query.all()]

    if form.validate_on_submit():
        if Trabajador.query.filter_by(nif=form.nif.data).first():
            flash(f'Error: El NIF {form.nif.data} ya existe.')
        elif Trabajador.query.filter_by(email=form.email.data).first():
            flash(f'Error: El Email {form.email.data} ya existe.')
        else:
            empleado = Trabajador()
            form.populate_obj(empleado)
            # Asignación manual de FKs para evitar problemas de mapping
            empleado.idRol = form.rol_id.data
            empleado.idHorario = form.horario_id.data
            empleado.idEmpresa = 1 
            
            db.session.add(empleado)
            db.session.commit()
            flash('Empleado creado correctamente.')
            return redirect(url_for('empleados.listar_empleados'))
            
    return render_template('editar_empleado.html', form=form, titulo="Nuevo Empleado")

@empleados_bp.route('/empleados/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_empleado(id):
    empleado = Trabajador.query.get_or_404(id)
    form = TrabajadorForm(obj=empleado)

    if request.method == 'GET':
        form.rol_id.data = empleado.idRol
        form.horario_id.data = empleado.idHorario

    if current_user.id_trabajador == id:
        roles_permitidos = Rol.query.filter(Rol.nombre_rol.in_(['Administrador', 'Superadministrador'])).all()
    else:
        roles_permitidos = Rol.query.filter(Rol.nombre_rol.notin_(['Administrador', 'Superadministrador'])).all()
        
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]
    form.horario_id.choices = [(h.id_horario, h.nombre_horario) for h in Horario.query.all()]

    if form.validate_on_submit():
        form.populate_obj(empleado)
        empleado.idRol = form.rol_id.data
        empleado.idHorario = form.horario_id.data
        db.session.commit()
        flash('Datos actualizados correctamente.')
        return redirect(url_for('empleados.listar_empleados'))

    return render_template('editar_empleado.html', form=form, titulo="Editar Perfil")

@empleados_bp.route('/empleados/eliminar/<int:id>')
@login_required
def eliminar_empleado(id):
    empleado = Trabajador.query.get_or_404(id)
    if empleado.id_trabajador == current_user.id_trabajador:
        flash('Error: No puedes eliminarte a ti mismo.')
    else:
        db.session.delete(empleado)
        db.session.commit()
        flash('Empleado eliminado.')
    return redirect(url_for('empleados.listar_empleados'))