# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class HrPayrollAdvice(models.Model):
    '''
    Bank Advice
    '''
    _name = 'hr.payroll.advice'
    _description = "Moroccan HR Payroll Advice"

    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    name = fields.Char(readonly=True, required=True, states={'draft': [('readonly', False)]})
    note = fields.Text(string='Description', default='Please make the payroll transfer from above account number to the below mentioned account numbers towards employee salaries:')
    date = fields.Date(readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_get_default_date,
        help='Advice Date is used to search Payslips')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', index=True, readonly=True)
    number = fields.Char(string='Reference', readonly=True)
    line_ids = fields.One2many('hr.payroll.advice.line', 'advice_id', string='Employee Salary',
        states={'draft': [('readonly', False)]}, readonly=True, copy=True)
    chaque_nos = fields.Char(string='Cheque Numbers')
    neft = fields.Boolean(string='NEFT Transaction', help='Check this box if your company use online transfer for salary')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, states={'draft': [('readonly', False)]},
        help='Select the Bank from which the salary is going to be paid')
    batch_id = fields.Many2one('hr.payslip.run', string='Batch', readonly=True)

    @api.multi
    def compute_advice(self):
        """
        Advice - Create Advice lines in Payment Advice and
        compute Advice lines.
        """
        for advice in self:
            old_lines = self.env['hr.payroll.advice.line'].search([('advice_id', '=', advice.id)])
            if old_lines:
                old_lines.unlink()
            payslips = self.env['hr.payslip'].search([('date_from', '<=', advice.date), ('date_to', '>=', advice.date), ('state', '=', 'done')])
            for slip in payslips:
                if not slip.employee_id.bank_account_id and not slip.employee_id.bank_account_id.acc_number:
                    raise UserError(_('Please define bank account for the %s employee') % (slip.employee_id.name,))
                payslip_line = self.env['hr.payslip.line'].search([('slip_id', '=', slip.id), ('code', '=', 'NET')], limit=1)
                if payslip_line:
                    self.env['hr.payroll.advice.line'].create({
                        'advice_id': advice.id,
                        'name': slip.employee_id.bank_account_id.acc_number,
                        'ifsc_code': slip.employee_id.bank_account_id.bank_bic or '',
                        'employee_id': slip.employee_id.id,
                        'bysal': payslip_line.total
                    })
                slip.advice_id = advice.id

    @api.multi
    def confirm_sheet(self):
        """
        confirm Advice - confirmed Advice after computing Advice Lines..
        """
        for advice in self:
            if not advice.line_ids:
                raise UserError(_('You can not confirm Payment advice without advice lines.'))
            date = fields.Date.from_string(fields.Date.today())
            advice_year = date.strftime('%m') + '-' + date.strftime('%Y')
            number = self.env['ir.sequence'].next_by_code('payment.advice')
            advice.write({
                'number': 'PAY' + '/' + advice_year + '/' + number,
                'state': 'confirm',
            })

    @api.multi
    def set_to_draft(self):
        """Resets Advice as draft.
        """
        self.write({'state': 'draft'})

    @api.multi
    def cancel_sheet(self):
        """Marks Advice as cancelled.
        """
        self.write({'state': 'cancel'})

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.bank_id = self.company_id.partner_id.bank_ids and self.company_id.partner_id.bank_ids[0].bank_id.id or False


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    _description = 'Payslip Batches'

    available_advice = fields.Boolean(string='Made Payment Advice?',
                                       help='If this box is checked which means that Payment Advice exists for current batch',
                                       readonly=False, copy=False)

    @api.multi
    def draft_payslip_run(self):
        super(HrPayslipRun, self).draft_payslip_run()
        self.write({'available_advice': False})

    @api.multi
    def create_advice(self):
        for run in self:
            if run.available_advice:
                raise UserError(_("Payment advice already exists for %s, 'Set to Draft' to create a new advice.") % (run.name,))
            company = self.env.user.company_id
            advice = self.env['hr.payroll.advice'].create({
                        'batch_id': run.id,
                        'company_id': company.id,
                        'name': run.name,
                        'date': run.date_end,
                        'bank_id': company.partner_id.bank_ids and company.partner_id.bank_ids[0].bank_id.id or False
                    })
            for slip in run.slip_ids:
                # TODO is it necessary to interleave the calls ?
                slip.action_payslip_done()
                if not slip.employee_id.bank_account_id or not slip.employee_id.bank_account_id.acc_number:
                    raise UserError(_('Please define bank account for the %s employee') % (slip.employee_id.name))
                payslip_line = self.env['hr.payslip.line'].search([('slip_id', '=', slip.id), ('code', '=', 'NET')], limit=1)
                if payslip_line:
                    self.env['hr.payroll.advice.line'].create({
                        'advice_id': advice.id,
                        'name': slip.employee_id.bank_account_id.acc_number,
                        'ifsc_code': slip.employee_id.bank_account_id.bank_bic or '',
                        'employee_id': slip.employee_id.id,
                        'bysal': payslip_line.total
                    })
        self.write({'available_advice': True})


class HrPayrollAdviceLine(models.Model):
    '''
    Bank Advice Lines
    '''
    _name = 'hr.payroll.advice.line'
    _description = 'Bank Advice Lines'

    advice_id = fields.Many2one('hr.payroll.advice', string='Bank Advice')
    name = fields.Char('Bank Account No.', required=True)
    ifsc_code = fields.Char(string='IFSC Code')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    bysal = fields.Float(string='By Salary', digits=dp.get_precision('Payroll'))
    debit_credit = fields.Char(string='C/D', default='C')
    company_id = fields.Many2one('res.company', related='advice_id.company_id', string='Company', store=True, readonly=False)
    ifsc = fields.Boolean(related='advice_id.neft', string='IFSC', readonly=False)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.name = self.employee_id.bank_account_id.acc_number
        self.ifsc_code = self.employee_id.bank_account_id.bank_bic or ''


class HrPayslip(models.Model):
    '''
    Employee Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slips'

    advice_id = fields.Many2one('hr.payroll.advice', string='Bank Advice', copy=False)

class HrContract(models.Model):
    """
    Employee contract allows to add different values in fields.
    Fields are used in salary rule computation.
    """
    _inherit = 'hr.contract'

    indemnite_transport = fields.Float(string='Indémnité de Transport', digits=dp.get_precision('payroll'), help='Indémnité de Transport')
    prime_panier = fields.Float(string='Prime de Panier', digits=dp.get_precision('payroll'),
    help='Prime de Panier')
    prime_fonction = fields.Float(string='Prime de Fonction', digits=dp.get_precision('payroll'),
    help='Prime de Fonction')
    indemnite_representation = fields.Float(string='Indémnité de Représentation', digits=dp.get_precision('payroll'),
    help='Indémnité de Représentation')
    indemnite_voiture = fields.Float(string='Indémnité de Voiture', digits=dp.get_precision('payroll'),
    help='Indémnité de Voiture')

class HRemployee(models.Model):
    _inherit = 'hr.employee'

    cin = fields.Char(string="Numéro CIN", required=False)
    #perso_email = fields.Char(string="Adresse Email Personnelle", required=False)
    matricule_cnss = fields.Char(string="Numéro CNSS", required=False)
    matricule_cimr = fields.Char(string="Numéro CIMR", required=False)
    cat_cimr = fields.Char(string="Catégorie CIMR", default='00', required=False)
    date_cimr = fields.Date(string="Date d'adhésion CIMR", required=False)
    matricule_mut = fields.Char(string="Numéro MUTUELLE", required=False)
    num_chezemployeur = fields.Integer(string="Matricule")
    bank_agence = fields.Char(string="Agence Bancaire", required=False)
    bank_company_id = fields.Many2one('res.bank', string='Banque de Virement', readonly=False,
        help='Sélectionner la banque par laquelle le salaire sera versé')
    charge_sociale = fields.Integer(string="Personnes à Charge", required=False, help='Nombre de Personnes à Charge Sociale pour déduction IR')

class ResCompany(models.Model):
    _inherit = 'res.company'

    affil_cnss = fields.Char(string="N° Affiliation CNSS")
    affil_cimr = fields.Char(string="N° Affiliation CIMR")
    taux_cimr_salar = fields.Char(string="Taux CIMR Salariale")
    taux_cimr_part = fields.Char(string="Taux CIMR Patronale")
    ice = fields.Char(string="I.C.E")
    patente = fields.Char(string="Patente N°")
    tp = fields.Char(string="Taxe Professionnelle")
    code_commune = fields.Char(string="Code Commune pour IR")
    bank = fields.One2many('res.partner.bank', 'bank_id')
    count_total = fields.Char(string="Nombre d'employés",)
    count_permanent = fields.Char(string="Nombre d'employés Permanents",)
    count_occas = fields.Char(string="Nombre d'employés Occasionnelles",)
    count_stag = fields.Char(string="Nombre de stagiaires",)

class FichePaieParser(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_payslip'
    _description = "Morocco Pay Slip"


    def get_payslip_lines(self, objs):
        res = []
        ids = []
        for item in objs:
            if item.appears_on_payslip is True and not item.salary_rule_id.parent_rule_id:
                ids.append(item.id)
        if ids:
            res = self.env['hr.payslip.line'].browse(ids)
        return res

    def get_total_by_rule_category(self, obj, code):
        category_total = 0
        category_id = self.env['hr.salary.rule.category'].search([('code', '=', code)], limit=1).id
        if category_id:
            line_ids = self.env['hr.payslip.line'].search([('slip_id', '=', obj.id), ('category_id', 'child_of', category_id)])
            for line in line_ids:
                category_total += line.total
        return category_total

    def get_employer_line(self, obj, parent_line):
        return self.env['hr.payslip.line'].search([('slip_id', '=', obj.id), ('salary_rule_id.parent_rule_id.id', '=', parent_line.salary_rule_id.id)], limit=1)

    @api.model
    def _get_report_values(self, docids, data=None):
        payslip = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'data': data,
            'docs': payslip,
            'lang': "fr_FR",
            'get_payslip_lines': self.get_payslip_lines,
            'get_total_by_rule_category': self.get_total_by_rule_category,
            'get_employer_line': self.get_employer_line,
        }

class ResBank(models.Model):
    _inherit = 'res.bank'

    bank_virement = fields.Many2one('res.partner.bank', string='Banque de paiement')
    bank_virement_id = fields.Many2one('res.bank', string='Banque de paiement', related='bank_virement.bank_id')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
