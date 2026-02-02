from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models import Horario, Franja, Dia
from app.forms import HorarioForm, FranjaForm

# Definimos el Blueprint para horarios
horarios_bp = Blueprint('horarios', __name__)

@horarios_bp.route('/horarios')
@login_required
def listar_horarios():
    horarios = Horario.query.all()
    return render_template('horarios.html', horarios=horarios)

@horarios_bp.route('/horarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_horario():
    form = HorarioForm()
    if form.validate_on_submit():
        horario = Horario(nombre_horario=form.nombre_horario.data, descripcion=form.descripcion.data)
        db.session.add(horario)
        db.session.commit()
        # Redirigimos a la vista de detalle del nuevo horario en este mismo blueprint
        return redirect(url_for('horarios.ver_horario', id=horario.id_horario))
    return render_template('editar_horario.html', form=form, titulo="Nuevo Horario")

@horarios_bp.route('/horarios/ver/<int:id>', methods=['GET', 'POST'])
@login_required
def ver_horario(id):
    horario = Horario.query.get_or_404(id)
    form = FranjaForm()
    form.dia_id.choices = [(d.id, d.nombre) for d in Dia.query.all()]

    if form.validate_on_submit():
        # Validación de solapamiento
        franjas = Franja.query.filter_by(id_horario=id, id_dia=form.dia_id.data).all()
        solapa = any((form.hora_entrada.data < f.hora_salida) and (form.hora_salida.data > f.hora_entrada) for f in franjas)

        if solapa:
            flash('Error: Solapamiento de horas.')
        else:
            franja = Franja(id_horario=id, id_dia=form.dia_id.data, hora_entrada=form.hora_entrada.data, hora_salida=form.hora_salida.data)
            db.session.add(franja)
            db.session.commit()
            return redirect(url_for('horarios.ver_horario', id=id))

    return render_template('ver_horario.html', horario=horario, form=form)

@horarios_bp.route('/horarios/eliminar/<int:id>')
@login_required
def eliminar_horario(id):
    horario = Horario.query.get_or_404(id)
    if horario.trabajadores.first():
        flash('Error: Horario asignado a empleados.')
    else:
        Franja.query.filter_by(id_horario=id).delete()
        db.session.delete(horario)
        db.session.commit()
    return redirect(url_for('horarios.listar_horarios'))

@horarios_bp.route('/franjas/eliminar/<int:id_horario>/<int:id_dia>')
@login_required
def eliminar_franja(id_horario, id_dia):
    Franja.query.filter_by(id_horario=id_horario, id_dia=id_dia).delete()
    db.session.commit()
    return redirect(url_for('horarios.ver_horario', id=id_horario))