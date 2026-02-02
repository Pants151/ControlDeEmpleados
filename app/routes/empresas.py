from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models import Empresa
from app.forms import EmpresaForm

# Definimos el Blueprint
empresas_bp = Blueprint('empresas', __name__)

@empresas_bp.route('/configuracion-empresa', methods=['GET', 'POST'])
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