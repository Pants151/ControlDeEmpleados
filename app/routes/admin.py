from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Empresa, Trabajador, Rol, Horario, Franja, Dia
from app.forms import EmpresaForm, TrabajadorForm, RolForm, HorarioForm, FranjaForm
from app.utils import superadmin_required
from sqlalchemy.orm import joinedload

admin_bp = Blueprint('admin', __name__)

# [GESTION DE EMPRESA]
@admin_bp.route('/configuracion-empresa', methods=['GET', 'POST'])
@login_required
def configuracion_empresa():
    empresa = Empresa.query.get_or_404(1)
    form = EmpresaForm(obj=empresa)

    if form.validate_on_submit():
        form.populate_obj(empresa)
        db.session.commit()
        flash('Datos de la empresa actualizados correctamente.')
        return redirect(url_for('main.index'))

    return render_template('editar_empresa.html', form=form, titulo="Configuración de Empresa")

# [GESTION DE EMPLEADOS]
@admin_bp.route('/empleados', methods=['GET', 'POST'])
@login_required
def listar_empleados():
    empresa_seleccionada_id = session.get('contexto_empresa')
    if empresa_seleccionada_id == 0: empresa_seleccionada_id = None

    if empresa_seleccionada_id:
        # Forzamos la carga de rol y horario para que aparezcan en la tabla tras crear el usuario
        empleados = Trabajador.query.options(
            joinedload(Trabajador.rol),
            joinedload(Trabajador.horario)
        ).filter_by(idEmpresa=empresa_seleccionada_id).all()
        empresa_obj = Empresa.query.get(empresa_seleccionada_id)
    else:
        empleados = Trabajador.query.filter_by(idEmpresa=None).all()
        empresa_obj = None

    return render_template('empleados.html', empleados=empleados, empresa_actual=empresa_obj)

@admin_bp.route('/empleados/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_empleado():
    form = TrabajadorForm()
    
    # FILTRO ROLES: Solo roles que no sean admin
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
            
            # ASIGNACION MANUAL: Corregimos el fallo de nombres entre Formulario y Modelo
            empleado.idRol = form.rol_id.data
            empleado.idHorario = form.horario_id.data
            empleado.idEmpresa = 1 # Empresa por defecto
            
            db.session.add(empleado)
            db.session.commit()
            flash('Empleado creado correctamente.')
            return redirect(url_for('admin.listar_empleados'))
            
    return render_template('editar_empleado.html', form=form, titulo="Nuevo Empleado")

@admin_bp.route('/empleados/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_empleado(id):
    empleado = Trabajador.query.get_or_404(id)
    form = TrabajadorForm(obj=empleado)

    if request.method == 'GET':
        form.rol_id.data = empleado.idRol
        form.horario_id.data = empleado.idHorario

    # FILTRO ROLES: Protegemos que no se asignen roles admin desde aquí
    if current_user.id_trabajador == id:
        # Si me edito a mí mismo, veo mis roles de admin
        roles_permitidos = Rol.query.filter(Rol.nombre_rol.in_(['Administrador', 'Superadministrador'])).all()
    else:
        # Si edito a otro, solo puedo asignarle roles de empleado
        roles_permitidos = Rol.query.filter(Rol.nombre_rol.notin_(['Administrador', 'Superadministrador'])).all()
        
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]
    form.horario_id.choices = [(h.id_horario, h.nombre_horario) for h in Horario.query.all()]

    if form.validate_on_submit():
        form.populate_obj(empleado)
        
        # ASIGNACION MANUAL: Corregimos el fallo de nombres aquí también
        empleado.idRol = form.rol_id.data
        empleado.idHorario = form.horario_id.data
        
        db.session.commit()
        flash('Datos actualizados correctamente.')
        return redirect(url_for('admin.listar_empleados'))

    return render_template('editar_empleado.html', form=form, titulo="Editar Perfil")

@admin_bp.route('/empleados/eliminar/<int:id>')
@login_required
def eliminar_empleado(id):
    empleado = Trabajador.query.get_or_404(id)
    if empleado.id_trabajador == current_user.id_trabajador:
        flash('Error: No puedes eliminarte a ti mismo.')
    else:
        db.session.delete(empleado)
        db.session.commit()
        flash('Empleado eliminado.')
    return redirect(url_for('admin.listar_empleados'))

# [RESTO DE RUTAS: ROLES Y HORARIOS IGUAL]
@admin_bp.route('/roles')
@login_required
def listar_roles():
    roles = Rol.query.all()
    return render_template('roles.html', roles=roles)

@admin_bp.route('/roles/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_rol():
    form = RolForm()
    if form.validate_on_submit():
        if Rol.query.filter_by(nombre_rol=form.nombre_rol.data).first():
            flash('Error: Ya existe ese rol.')
        else:
            rol = Rol(nombre_rol=form.nombre_rol.data)
            db.session.add(rol)
            db.session.commit()
            return redirect(url_for('admin.listar_roles'))
    return render_template('editar_rol.html', form=form, titulo="Nuevo Rol")

@admin_bp.route('/roles/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_rol(id):
    rol = Rol.query.get_or_404(id)
    form = RolForm(obj=rol)
    if form.validate_on_submit():
        rol.nombre_rol = form.nombre_rol.data
        db.session.commit()
        return redirect(url_for('admin.listar_roles'))
    return render_template('editar_rol.html', form=form, titulo="Editar Rol")

@admin_bp.route('/roles/eliminar/<int:id>')
@login_required
def eliminar_rol(id):
    rol = Rol.query.get_or_404(id)
    if rol.trabajadores.first():
        flash('Error: Rol asignado a empleados.')
    else:
        db.session.delete(rol)
        db.session.commit()
    return redirect(url_for('admin.listar_roles'))

@admin_bp.route('/horarios')
@login_required
def listar_horarios():
    horarios = Horario.query.all()
    return render_template('horarios.html', horarios=horarios)

@admin_bp.route('/horarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_horario():
    form = HorarioForm()
    if form.validate_on_submit():
        horario = Horario(nombre_horario=form.nombre_horario.data, descripcion=form.descripcion.data)
        db.session.add(horario)
        db.session.commit()
        return redirect(url_for('admin.ver_horario', id=horario.id_horario))
    return render_template('editar_horario.html', form=form, titulo="Nuevo Horario")

@admin_bp.route('/horarios/ver/<int:id>', methods=['GET', 'POST'])
@login_required
def ver_horario(id):
    horario = Horario.query.get_or_404(id)
    form = FranjaForm()
    form.dia_id.choices = [(d.id, d.nombre) for d in Dia.query.all()]

    if form.validate_on_submit():
        franjas = Franja.query.filter_by(id_horario=id, id_dia=form.dia_id.data).all()
        solapa = any((form.hora_entrada.data < f.hora_salida) and (form.hora_salida.data > f.hora_entrada) for f in franjas)

        if solapa:
            flash('Error: Solapamiento de horas.')
        else:
            franja = Franja(id_horario=id, id_dia=form.dia_id.data, hora_entrada=form.hora_entrada.data, hora_salida=form.hora_salida.data)
            db.session.add(franja)
            db.session.commit()
            return redirect(url_for('admin.ver_horario', id=id))

    return render_template('ver_horario.html', horario=horario, form=form)

@admin_bp.route('/horarios/eliminar/<int:id>')
@login_required
def eliminar_horario(id):
    horario = Horario.query.get_or_404(id)
    if horario.trabajadores.first():
        flash('Error: Horario asignado a empleados.')
    else:
        Franja.query.filter_by(id_horario=id).delete()
        db.session.delete(horario)
        db.session.commit()
    return redirect(url_for('admin.listar_horarios'))

@admin_bp.route('/franjas/eliminar/<int:id_horario>/<int:id_dia>')
@login_required
def eliminar_franja(id_horario, id_dia):
    Franja.query.filter_by(id_horario=id_horario, id_dia=id_dia).delete()
    db.session.commit()
    return redirect(url_for('admin.ver_horario', id=id_horario))