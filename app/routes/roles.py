from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models import Rol
from app.forms import RolForm

# Definimos el Blueprint para roles
roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/roles')
@login_required
def listar_roles():
    roles = Rol.query.all()
    return render_template('roles.html', roles=roles)

@roles_bp.route('/roles/nuevo', methods=['GET', 'POST'])
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
            return redirect(url_for('roles.listar_roles'))
    return render_template('editar_rol.html', form=form, titulo="Nuevo Rol")

@roles_bp.route('/roles/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_rol(id):
    rol = Rol.query.get_or_404(id)
    form = RolForm(obj=rol)
    if form.validate_on_submit():
        rol.nombre_rol = form.nombre_rol.data
        db.session.commit()
        return redirect(url_for('roles.listar_roles'))
    return render_template('editar_rol.html', form=form, titulo="Editar Rol")

@roles_bp.route('/roles/eliminar/<int:id>')
@login_required
def eliminar_rol(id):
    rol = Rol.query.get_or_404(id)
    if rol.trabajadores.first():
        flash('Error: Rol asignado a empleados.')
    else:
        db.session.delete(rol)
        db.session.commit()
    return redirect(url_for('roles.listar_roles'))