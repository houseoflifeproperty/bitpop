// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/plugins/plugin_observer.h"

#include "base/auto_reset.h"
#include "base/bind.h"
#include "base/debug/crash_logging.h"
#include "base/metrics/histogram.h"
#include "base/stl_util.h"
#include "base/strings/utf_string_conversions.h"
#include "chrome/browser/browser_process.h"
#include "chrome/browser/content_settings/host_content_settings_map.h"
#include "chrome/browser/infobars/confirm_infobar_delegate.h"
#include "chrome/browser/infobars/infobar_service.h"
#include "chrome/browser/infobars/simple_alert_infobar_delegate.h"
#include "chrome/browser/lifetime/application_lifetime.h"
#include "chrome/browser/metrics/metrics_service.h"
#include "chrome/browser/plugins/plugin_finder.h"
#include "chrome/browser/plugins/plugin_infobar_delegates.h"
#include "chrome/browser/plugins/plugin_metadata.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/tab_modal_confirm_dialog.h"
#include "chrome/common/render_messages.h"
#include "chrome/common/url_constants.h"
#include "components/infobars/core/infobar.h"
#include "content/public/browser/plugin_service.h"
#include "content/public/browser/render_frame_host.h"
#include "content/public/browser/render_view_host.h"
#include "content/public/browser/web_contents.h"
#include "content/public/browser/web_contents_delegate.h"
#include "content/public/common/webplugininfo.h"
#include "grit/generated_resources.h"
#include "grit/theme_resources.h"
#include "ui/base/l10n/l10n_util.h"

#if defined(ENABLE_PLUGIN_INSTALLATION)
#if defined(OS_WIN)
#include "base/win/metro.h"
#endif
#include "chrome/browser/plugins/plugin_installer.h"
#include "chrome/browser/plugins/plugin_installer_observer.h"
#include "chrome/browser/ui/tab_modal_confirm_dialog_delegate.h"
#endif  // defined(ENABLE_PLUGIN_INSTALLATION)

using content::OpenURLParams;
using content::PluginService;
using content::Referrer;
using content::WebContents;

DEFINE_WEB_CONTENTS_USER_DATA_KEY(PluginObserver);

namespace {

#if defined(ENABLE_PLUGIN_INSTALLATION)

// ConfirmInstallDialogDelegate ------------------------------------------------

class ConfirmInstallDialogDelegate : public TabModalConfirmDialogDelegate,
                                     public WeakPluginInstallerObserver {
 public:
  ConfirmInstallDialogDelegate(content::WebContents* web_contents,
                               PluginInstaller* installer,
                               scoped_ptr<PluginMetadata> plugin_metadata);

  // TabModalConfirmDialogDelegate methods:
  virtual base::string16 GetTitle() OVERRIDE;
  virtual base::string16 GetDialogMessage() OVERRIDE;
  virtual base::string16 GetAcceptButtonTitle() OVERRIDE;
  virtual void OnAccepted() OVERRIDE;
  virtual void OnCanceled() OVERRIDE;

  // WeakPluginInstallerObserver methods:
  virtual void DownloadStarted() OVERRIDE;
  virtual void OnlyWeakObserversLeft() OVERRIDE;

 private:
  content::WebContents* web_contents_;
  scoped_ptr<PluginMetadata> plugin_metadata_;
};

ConfirmInstallDialogDelegate::ConfirmInstallDialogDelegate(
    content::WebContents* web_contents,
    PluginInstaller* installer,
    scoped_ptr<PluginMetadata> plugin_metadata)
    : TabModalConfirmDialogDelegate(web_contents),
      WeakPluginInstallerObserver(installer),
      web_contents_(web_contents),
      plugin_metadata_(plugin_metadata.Pass()) {
}

base::string16 ConfirmInstallDialogDelegate::GetTitle() {
  return l10n_util::GetStringFUTF16(
      IDS_PLUGIN_CONFIRM_INSTALL_DIALOG_TITLE, plugin_metadata_->name());
}

base::string16 ConfirmInstallDialogDelegate::GetDialogMessage() {
  return l10n_util::GetStringFUTF16(IDS_PLUGIN_CONFIRM_INSTALL_DIALOG_MSG,
                                    plugin_metadata_->name());
}

base::string16 ConfirmInstallDialogDelegate::GetAcceptButtonTitle() {
  return l10n_util::GetStringUTF16(
      IDS_PLUGIN_CONFIRM_INSTALL_DIALOG_ACCEPT_BUTTON);
}

void ConfirmInstallDialogDelegate::OnAccepted() {
  installer()->StartInstalling(plugin_metadata_->plugin_url(), web_contents_);
}

void ConfirmInstallDialogDelegate::OnCanceled() {
}

void ConfirmInstallDialogDelegate::DownloadStarted() {
  Cancel();
}

void ConfirmInstallDialogDelegate::OnlyWeakObserversLeft() {
  Cancel();
}
#endif  // defined(ENABLE_PLUGIN_INSTALLATION)

const char* kEnableJavaByDefaultForTheseDomains[] = {
  "1stnationalbank.com",
  "53.com",
  "77bank.co.jp",
  "aabar.com",
  "aareal-bank.com",
  "ab.lv",
  "abcbrasil.com.br",
  "abchina.com",
  "ablv.com",
  "abnamro.cl",
  "abnamro.com",
  "abnamro.nl",
  "abnamroprivatebanking.com",
  "aboutsantander.co.uk",
  "accbank.com",
  "accbank.ie",
  "accival.com.mx",
  "adcb.com",
  "adcbactive.com",
  "adib.ae",
  "advanzia.com",
  "aegon.com",
  "aegonbank.nl",
  "afbank.com",
  "afbca.com",
  "afcmerchantbank.com",
  "affin.com.my",
  "affinbank.com.my",
  "afgrp.com",
  "aforebanamex.com.mx",
  "aforeinbursa.com.mx",
  "agfirst.com",
  "aib.ie",
  "aibcm.com",
  "aibcorporate.ie",
  "aibgb.co.uk",
  "aibgroup.com",
  "aibifs.com",
  "aibinternational.co.im",
  "aibjerseyisleofman.com",
  "aichibank.co.jp",
  "akb.ch",
  "al-bank.dk",
  "alahli.com",
  "alfransi.com.sa",
  "alhilalbank.ae",
  "ally.com",
  "almbrand.dk",
  "alpha.gr",
  "alrajhibank.com",
  "alterna.ca",
  "americanexpress.com",
  "amerisbank.com",
  "amp.com.au",
  "anb.com.sa",
  "andbank-monaco.mc",
  "andelskassen.dk",
  "anz.co.nz",
  "anz.com",
  "appkb.ch",
  "argenta.be",
  "asb.co.nz",
  "asbhawaii.com",
  "asnbank.nl",
  "atebank.de",
  "athloncarlease.com",
  "atticabank.gr",
  "autobank.at",
  "axa.be",
  "axabanque.fr",
  "b2bbank.com",
  "baj.com.sa",
  "baltikums.eu",
  "baltikums.lv",
  "banamex.com",
  "banca-e.com",
  "bancaditalia.it",
  "bancaesperia.it",
  "bancaja.es",
  "bancamediolanum.it",
  "bancoazteca.com.mx",
  "bancoazteca.com.pa",
  "bancoazteca.com.pe",
  "bancoazteca.com.sv",
  "bancobest.pt",
  "bancobic.pt",
  "bancobisel.com.ar",
  "bancobpi.pt",
  "bancochile.cl",
  "bancodelbajio.com.mx",
  "bancodevalencia.es",
  "bancoestado.cl",
  "bancoetcheverria.es",
  "bancofinancieroydeahorros.com",
  "bancofrances.com.ar",
  "bancogalicia.com",
  "bancoinbursa.com",
  "bancomediolanum.es",
  "bancomer.com",
  "bancomer.com.mx",
  "bancomext.com",
  "bancoparis.cl",
  "bancopastor.es",
  "bancopatagonia.com.ar",
  "bancopenta.cl",
  "bancopopolare.it",
  "bancopopular.es",
  "bancopopular.pt",
  "bancoripley.cl",
  "bancosabadellmiami.com",
  "bancovotorantim.com.br",
  "bancsabadell.com",
  "banesto.es",
  "banif.pt",
  "bank.lv",
  "bankaustria.at",
  "bankcomm.com",
  "bankcoop.ch",
  "bankia.com",
  "bankia.es",
  "bankinter.com",
  "banklenz.de",
  "banknh.com",
  "banknordik.dk",
  "banknorwegian.no",
  "bankofamerica.com",
  "bankofamerica.com.mx",
  "bankofbaroda.com",
  "bankofbotetourt.com",
  "bankofcanada.ca",
  "bankofcyprus.co.uk",
  "bankofcyprus.com",
  "bankofcyprus.com.cy",
  "bankofcyprus.com.ua",
  "bankofcyprus.gr",
  "bankofcyprus.ro",
  "bankofengland.co.uk",
  "bankofhamptonroads.com",
  "bankofindia.com",
  "bankofireland.com",
  "bankofireland.ie",
  "bankofirelandmortgages.co.uk",
  "bankofnc.com",
  "bankofnevada.com",
  "bankofscotland.co.uk",
  "bankofscotland.nl",
  "bankofsingapore.com",
  "bankoncit.com",
  "bankpime.es",
  "banksa.com.au",
  "banksterling.com",
  "bankwest.ca",
  "bankwest.com.au",
  "bankzweiplus.ch",
  "banorte-generali.com",
  "banorte-ixe.com.mx",
  "banorte.com",
  "banque-france.fr",
  "banque-pasche-group.com",
  "banquedeluxembourg.com",
  "banquedirecte.fr",
  "banquehavilland.com",
  "banqueinvik.se",
  "banquepopulaire.fr",
  "banregio.com",
  "banxico.org.mx",
  "bapro.com.ar",
  "barcap.com",
  "barclays.co.uk",
  "barclays.com",
  "barclays.pt",
  "barclaysstockbrokers.co.uk",
  "barclayswealth.com",
  "barodanzltd.co.nz",
  "bawagpsk.com",
  "bayernlb.de",
  "bb.com.br",
  "bb.com.mx",
  "bbk.es",
  "bbva.com",
  "bbva.com",
  "bbva.pt",
  "bbvacompass.com",
  "bc.gov.br",
  "bccbrescia.it",
  "bcee.lu",
  "bcentral.cl",
  "bcf.ch",
  "bcge.ch",
  "bci.cl",
  "bcimiami.com",
  "bcl.lu",
  "bcra.gov.ar",
  "bcv.ch",
  "bdc.ca",
  "bde.es",
  "bekb.ch",
  "bendigoadelaide.com.au",
  "bendigobank.com.au",
  "bes.pt",
  "best.pt",
  "bgl.lu",
  "bgz.pl",
  "bib.eu",
  "bib.lv",
  "bil.com",
  "binck.com",
  "binck.nl",
  "birchhillequity.com",
  "bis.org",
  "bkb.ch",
  "bmedonline.es",
  "bmedonline.it",
  "bmn.es",
  "bmo.com",
  "bmocm.com",
  "bna.com.ar",
  "bnbank.no",
  "bndes.gov.br",
  "bnm.gov.my",
  "bnpparibas.com",
  "bnpparibas.com.ar",
  "bnpparibasfortis.be",
  "bnu.com.mo",
  "bnymellon.com",
  "bnz.co.nz",
  "boc.cn",
  "bocomny.com",
  "boiusa.com",
  "boj.or.jp",
  "bok.or.kr",
  "boq.com.au",
  "boy.co.jp",
  "bpb.it",
  "bpce.fr",
  "bpm.it",
  "bpo.be",
  "bportugal.pt",
  "bpv.it",
  "bradesco.com.br",
  "bred.fr",
  "bremerlandesbank.de",
  "bridgewaterbank.ca",
  "bridgewaterbankmn.com",
  "britannia.co.uk",
  "bsibank.com",
  "bsp.com.fj",
  "bsp.com.pg",
  "bsp.com.sb",
  "bundesbank.de",
  "busanbank.co.kr",
  "ca-cib.com",
  "caisse-epargne.fr",
  "caissedesdepots.fr",
  "caixa.gov.br",
  "caixabank.com",
  "caixacapitalizacao.com.br",
  "caixacatalunya.com",
  "caixacultural.com.br",
  "caixagalicia.es",
  "caixaseguros.com.br",
  "caixavidaeprevidencia.com.br",
  "cajaespana-duero.es",
  "cajamadrid.com",
  "cam.es",
  "canadiantire.ca",
  "capitalone.ca",
  "capitalone.com",
  "carnegie.lu",
  "carnegie.se",
  "casden.fr",
  "castlebank.com",
  "catalunyacaixa.com",
  "cbd.ae",
  "cbonline.co.uk",
  "cbscanterbury.co.nz",
  "cbutah.com",
  "ccb.com",
  "ccbusa.com",
  "cdb.com.cn",
  "ceb.cz",
  "cebbank.com",
  "centralbankutah.com",
  "cfm.mc",
  "cfs.co.uk",
  "cgd.pt",
  "chibabank.co.jp",
  "cibc.com",
  "cic.com.sg",
  "cic.fr",
  "cimb-principal.com.my",
  "cimb-principalislamic.com",
  "cimb.com",
  "cimbbank.com.kh",
  "cimbbank.com.my",
  "cimbbank.com.sg",
  "cimbislamic.com",
  "cimbniaga.com",
  "cimbniagasyariah.com",
  "cimbsecurities.com",
  "cimbthai.com",
  "cit.com",
  "citi.co.nz",
  "citi.com",
  "citibanamex.com",
  "citibank.ca",
  "citibank.co.uk",
  "citibank.com",
  "citibank.com.sg",
  "citicards.ca",
  "citifinancial.ca",
  "citizensbank.ca",
  "citizensbank.com",
  "citizensbankfx.ca",
  "citynationalcm.com",
  "claridenleu.com",
  "cmb.mc",
  "cmbc.com.cn",
  "cmbchina.com",
  "cnb.com",
  "cnb.cz",
  "co-operativebank.co.nz",
  "co-operativebank.co.uk",
  "co-operativebankinggroup.co.uk",
  "co-operativeinsurance.co.uk",
  "co-operativeinvestments.co.uk",
  "coletaylor.com",
  "comerica.com",
  "commbank.com.au",
  "commercebank.com",
  "commerzbank.com",
  "commerzbank.lu",
  "compartamos.com",
  "concorsimediolanum.it",
  "consultorbancapersonal.es",
  "corpbanca.cl",
  "cpb.gr",
  "credem.it",
  "credit-agricole.com",
  "credit-agricole.ro",
  "credit-cooperatif.coop",
  "credit-cooperatif.fr",
  "credit-du-nord.fr",
  "credit-suisse.com",
  "crediteurope.be",
  "crediteurope.ch",
  "crediteurope.com.mt",
  "crediteurope.com.ua",
  "crediteurope.de",
  "crediteurope.nl",
  "crediteurope.ro",
  "crediteurope.ru",
  "crediteuropebank.com",
  "crediteuropeleasing.ru",
  "creditmobilierdemonaco.com",
  "creditmutuel.fr",
  "creditonebank.com",
  "creditonefriends.com",
  "crelan.be",
  "cresco.no",
  "csas.cz",
  "csob.cz",
  "ctfs.com",
  "cwbank.com",
  "cwbankgroup.com",
  "danskebank.com",
  "danskebank.ie",
  "danskebank.lv",
  "danskebank.no",
  "danskebank.se",
  "db.com",
  "dbc.ca",
  "dbs.com",
  "dcbank.ca",
  "dedhamsavings.com",
  "degussa-bank.de",
  "delagelanden.com",
  "delen.lu",
  "deutsche-bank.de",
  "deutschebank.com",
  "dexia-privatebanking.com",
  "dexia.be",
  "dgbfg.co.kr",
  "dhbbank.com",
  "dib.ae",
  "directaccess.com.my",
  "dkb.co.jp",
  "dkb.de",
  "dnb.lv",
  "dnb.nl",
  "dnb.no",
  "dnbnor.com",
  "dresdner-bank.com",
  "duncanlawrie.com",
  "dundeewealth.com",
  "dvbbank.com",
  "dz-privatbank.com",
  "dzbank.com",
  "e-private.com",
  "easybank.at",
  "ecitic.com",
  "edmond-de-rothschild.com",
  "edmond-de-rothschild.eu",
  "efgbank.com",
  "efggroup.com",
  "efginternational.com",
  "efirstbank.com",
  "egg.com",
  "ekspressbank.no",
  "emiratesislamicbank.ae",
  "emiratesnbd.com",
  "emporiki.gr",
  "ersteprivatebanking.at",
  "esfg.com",
  "eurobank.gr",
  "eurohypo.com",
  "europabank.be",
  "expobank.eu",
  "falconbank.com",
  "falconnational.com",
  "falconpb.com",
  "falconprivatebank.com",
  "familybanker.it",
  "farmcreditbank.com",
  "fbbank.gr",
  "fgb.ae",
  "fibabanka.com.tr",
  "fih.dk",
  "financenow.co.nz",
  "fininvest.it",
  "firstnational.com",
  "firsttrustbank.co.uk",
  "five-starbank.com",
  "fnbc.ca",
  "fnbk.com",
  "fnbsd.com",
  "fnni.com",
  "fnsouthwest.com",
  "fokus.no",
  "fokus.no",
  "forex.fi",
  "forex.no",
  "forex.se",
  "forexbank.dk",
  "forextrading.com",
  "fortis.nl",
  "fortuna.lu",
  "freo.nl",
  "frieslandbank.nl",
  "fukuokabank.co.jp",
  "gemoneybank.lv",
  "generalbank.ca",
  "generali.com",
  "geniki.gr",
  "gfgsa.com",
  "gkb.ch",
  "glkb.ch",
  "golifestore.com",
  "greatwesternbank.com",
  "groupama.com",
  "grupobancopopular.com",
  "grupobancosabadell.com",
  "gruppobancasella.it",
  "gruppocarige.it",
  "gruppoesperia.it",
  "gruppovenetobanca.it",
  "habibbank.com",
  "halifax.co.uk",
  "hanabank.com",
  "handelsbanken.co.uk",
  "handelsbanken.fi",
  "handelsbanken.lv",
  "handelsbanken.nl",
  "handelsbanken.no",
  "handelsbanken.se",
  "handelsbanken.us",
  "hbru.ru",
  "hbsbank.co.nz",
  "hbsnz.com",
  "heartland.co.nz",
  "helaba-invest.de",
  "helaba-trust.de",
  "helaba.de",
  "hellenicbank.com",
  "hellenicnetbanking.com",
  "heritage.com.au",
  "hipo.lv",
  "hipotecario.com.ar",
  "homequitybank.ca",
  "hottinger.co.uk",
  "hottinger.com",
  "hottinger.lu",
  "hsbc.ae",
  "hsbc.ca",
  "hsbc.cl",
  "hsbc.co.in",
  "hsbc.co.uk",
  "hsbc.com",
  "hsbc.com.ar",
  "hsbc.com.br",
  "hsbc.com.cn",
  "hsbc.com.mx",
  "hsbc.com.sg",
  "hsbc.fr",
  "hsbc.gr",
  "hsbcprivatebankfrance.com",
  "hsh-nordbank.com",
  "hsh-nordbank.de",
  "hxb.com.cn",
  "hypo-alpe-adria.com",
  "hypothekenbankfrankfurt.com",
  "hypotirol.com",
  "hypovbg.at",
  "hypovereinsbank.de",
  "ibk.co.kr",
  "icbc.com.ar",
  "icbc.com.cn",
  "icicibank.com",
  "ifsag.ch",
  "ikano.co.uk",
  "ikano.no",
  "ikanobank.com",
  "ikanobank.de",
  "ikanobank.dk",
  "ikanobank.fi",
  "ikanobank.pl",
  "ikanobank.se",
  "ikanogroup.com",
  "ikb.de",
  "inbursa.com",
  "inbursa.com.mx",
  "inbweb.com",
  "ing.be",
  "ing.com",
  "ingcasadebolsa.com",
  "ingcommercialbanking.com",
  "ingdirect.ca",
  "ingdirect.com.au",
  "inggrupofinanciero.com",
  "intesasanpaolo.com",
  "ipic.ae",
  "irishlife.ie",
  "irishlifepermanent.ie",
  "isdb.org",
  "itau.cl",
  "itau.co.jp",
  "itau.com",
  "itau.com.ar",
  "itau.com.br",
  "itau.com.py",
  "itau.com.uy",
  "itauprivatebank.com",
  "itausecurities.com",
  "ixe.com.mx",
  "jamesonbank.com",
  "japanpost.jp",
  "jbic.go.jp",
  "jpmorganchase.com",
  "jsafrasarasin.com",
  "juliusbaer.com",
  "juliusbaer.com",
  "jyskebank.com",
  "jyskebank.dk",
  "kasbank.com",
  "kb.cz",
  "kbc.be",
  "kbc.com",
  "kbc.ie",
  "kbc.ie",
  "kbstar.com",
  "kdb.co.kr",
  "keb.co.kr",
  "kempen.nl",
  "key.com",
  "keytradebank.com",
  "keytradebank.nl",
  "kfw.de",
  "kiwibank.co.nz",
  "kjbank.com",
  "kommunalkredit.at",
  "kutxa.net",
  "kutxabank.es",
  "kyotobank.co.jp",
  "labanquepostale.fr",
  "lacaixa.com",
  "laconiasavings.com",
  "landbobanken.dk",
  "landkreditt.no",
  "landkredittbank.no",
  "laposte.fr",
  "lasergroup.eu",
  "laurentianbank.com",
  "lbb.de",
  "lbb.lv",
  "lbbw.de",
  "lbbw.lu",
  "lblux.lu",
  "lcl.com",
  "lgt-capital-partners.com",
  "lgt.com",
  "liberbank.es",
  "libertyhomefinancial.com",
  "lkb.lv",
  "lloydsbankinggroup.com",
  "lloydstsb.com",
  "lombardodier.com",
  "lukb.ch",
  "lutherburbanksavings.com",
  "macquarie.com.au",
  "macro.com.ar",
  "mangroupplc.com",
  "manulife.com",
  "manulifebank.ca",
  "marac.co.nz",
  "martinmaurel.com",
  "mas.gov.sg",
  "mashreqbank.com",
  "maybank.com.my",
  "maybank2u.com.sg",
  "mbfinancial.com",
  "mbna.ca",
  "mediobanca.it",
  "mediolanum.com",
  "mediolanum.it",
  "mediolanumcorporateuniversity.it",
  "mediolanumgestionefondi.it",
  "mediolanuminternationalfunds.it",
  "mediolanuminternationallife.it",
  "mediolanumprimafila.it",
  "mediolanumprivatebanker.it",
  "mediolanumresidence.it",
  "mediolanumvita.it",
  "meespierson.an",
  "meespierson.nl",
  "meigin.com",
  "mercantildobrasil.com.br",
  "millenniumbank.gr",
  "millenniumbcp.pt",
  "mizuho-fg.co.jp",
  "mmwarburg.lu",
  "moncana.com",
  "monex.com.mx",
  "monteparma.it",
  "montepaschi.be",
  "montepio.pt",
  "morganstanley.com",
  "mps.it",
  "mufg.jp",
  "myctfs.com",
  "mywealthcareonline.com",
  "nab.com.au",
  "nabgroup.com",
  "nantobank.co.jp",
  "naspadub.ie",
  "nationalbank.co.nz",
  "nationalirishbank.ie",
  "nationalirishbank.ie",
  "nationwide.co.uk",
  "nationwideinternational.com",
  "natixis.com",
  "natwest.com",
  "nbad.com",
  "nbb.be",
  "nbc.ca",
  "nbg.gr",
  "newyorkcommercialbank.com",
  "nibc.nl",
  "nkb.ch",
  "nochubank.or.jp",
  "nomura.com",
  "nomuraholdings.com",
  "nonghyup.com",
  "noorbank.com",
  "noorinternetbanking.com",
  "nordea.com",
  "nordea.dk",
  "nordea.lu",
  "nordea.lv",
  "nordea.no",
  "nordeaprivatebanking.no",
  "nordlandsbanken.no",
  "nordlb.com",
  "nordlb.de",
  "norges-bank.no",
  "northernbank.co.uk",
  "norvik.lv",
  "norwaysavingsbank.com",
  "nossacaixa.com.br",
  "novacaixagalicia.es",
  "nrsbank.dk",
  "nykredit.com",
  "nykredit.dk",
  "oberbank.at",
  "obvion.nl",
  "ocbc.com",
  "oddo.eu",
  "oddo.fr",
  "oekb.at",
  "oenb.at",
  "oest.no",
  "oitabank.co.jp",
  "orbay.nl",
  "pacecu.ca",
  "panelliniabank.gr",
  "pasche.ch",
  "passbanca.it",
  "patria-finance.com",
  "pbebank.com",
  "pbgate.net",
  "pcfinancial.ca",
  "permanenttsb.ie",
  "permanenttsbgroup.ie",
  "pggwrightsonfinance.co.nz",
  "pictet.com",
  "pioneerbnk.com",
  "pioneerelpaso.com",
  "pioneermidland.com",
  "pioneersb.com",
  "piraeusbank.gr",
  "pnc.com",
  "postbank.com",
  "previred.com",
  "probank.gr",
  "proton.gr",
  "psbc.com",
  "psd-berlin-brandenburg.de",
  "puertoricofarmcredit.com",
  "pwbank.com",
  "rabobank.be",
  "rabobank.co.nz",
  "rabodirect.co.nz",
  "rabovastgoedgroep.nl",
  "raiffeisen.ch",
  "raiffeisen.lu",
  "rakbank.ae",
  "rakbankdirect.ae",
  "rakbankonline.ae",
  "rb.cz",
  "rba.gov.au",
  "rbc.com",
  "rbcadvicecentre.com",
  "rbcbank.com",
  "rbccm.com",
  "rbcdirectinvesting.com",
  "rbcds.com",
  "rbcgam.com",
  "rbcinsurance.com",
  "rbcis.com",
  "rbcroyalbank.com",
  "rbcwealthmanagement.com",
  "rbcwminternational.com",
  "rbnz.govt.nz",
  "rbs.co.uk",
  "rbs.com",
  "rbs.nl",
  "regiobank.nl",
  "regions.com",
  "reliancebank.com",
  "rembrandt-fo.nl",
  "resona-gr.co.jp",
  "reverta.lv",
  "rhb.com.my",
  "rhbbank.com.sg",
  "rietumu.com",
  "riksbank.se",
  "riyadbank.com",
  "riyadbank.com.sa",
  "robeco.com",
  "robeco.fr",
  "rothschild.com",
  "rothschildbank.com",
  "ruralvia.com",
  "rzb.at",
  "saarlb.de",
  "sabb.com",
  "sabbtakaful.com",
  "sabinebank.com",
  "safra.com.br",
  "sagabank.co.jp",
  "saib.com",
  "salliemae.com",
  "samba.com",
  "sampopankki.fi",
  "sanostra.es",
  "santander.cl",
  "santander.co.uk",
  "santander.com",
  "santander.com.br",
  "santander.com.mx",
  "santander.no",
  "santanderconsumer.com",
  "santanderrio.com.ar",
  "santandertotta.pt",
  "sarasin.ch",
  "sarasin.com",
  "saxobank.com",
  "saxoprivatbank.com",
  "saxoworld.com",
  "sberbankcz.cz",
  "sbi.co.in",
  "sbiuk.com",
  "sbs.net.nz",
  "sbsbank.co.nz",
  "schoellerbank.at",
  "schretlen.com",
  "schroders.com",
  "scotiabank.cl",
  "scotiabank.com",
  "seb.lv",
  "seb.se",
  "sebgroup.com",
  "securitybankkc.com",
  "segurosbanamex.com.mx",
  "segurosinbursa.com.mx",
  "sella.it",
  "sgkb.ch",
  "sgkb.ch",
  "sgkb.de",
  "shb.com.sa",
  "shinhan.com",
  "shinseibank.com",
  "sib.ae",
  "skandiabanken.no",
  "skandiabanken.se",
  "smfg.co.jp",
  "smile.co.uk",
  "smn.no",
  "smpbank.com",
  "smpbank.lv",
  "smpbank.ru",
  "snb.ch",
  "snci.lu",
  "snsreaal.nl",
  "societegenerale.com",
  "societegenerale.fr",
  "societegenerale.mc",
  "sofinco.com",
  "southsure.co.nz",
  "spaengler.at",
  "sparda-b.de",
  "sparebank1.no",
  "sparkron.dk",
  "sparlolland.dk",
  "sparnord.dk",
  "spks.dk",
  "spv.no",
  "sr-bank.no",
  "standardchartered.ae",
  "standardchartered.co.th",
  "standardchartered.co.za",
  "standardchartered.com",
  "standardchartered.com.cn",
  "standardchartered.com.hk",
  "standardchartered.com.my",
  "standardchartered.com.sg",
  "standardlife.ca",
  "standardlife.co.uk",
  "standardlife.com",
  "standardlifeinvestments.com",
  "standardlifewealth.com",
  "statebankofindia.com",
  "statestreet.com",
  "steiermaerkische.at",
  "sterlingfinancialcorporation-spokane.com",
  "sterlingsavingsbank.com ",
  "stgeorge.com.au",
  "storebrand.no",
  "suncorp.com.au",
  "suncorpbank.com.au",
  "suntrust.com",
  "svb.com",
  "swedbank.lv",
  "swedbank.se",
  "swissbanking.org",
  "sydbank.dk",
  "tarjetanaranja.com",
  "tbank.com.gr",
  "td.com",
  "tdcanadatrust.com",
  "tesco.com",
  "tescobank.com",
  "texasbankandtrust.com",
  "texascapitalbank.com",
  "tkb.ch",
  "tkb.lv",
  "totalbank.com",
  "tradingfloor.com",
  "triodos.co.uk",
  "triodos.com",
  "triodos.nl",
  "tsb.co.nz",
  "tsbrealty.co.nz",
  "tsbtrust.org.nz",
  "ttbank.gr",
  "uab.ae",
  "ubibanca.it",
  "ubp.com",
  "ubpbank.com",
  "ubs.com",
  "ulsterbank.co.uk",
  "ulsterbank.com",
  "ulsterbank.ie",
  "unb.com",
  "unicaja.es",
  "unico.nl",
  "unicreditbank.cz",
  "unicreditbank.ie",
  "unicreditbank.lv",
  "unicreditgroup.eu",
  "unionbank.com",
  "uobgroup.com",
  "usaa.com",
  "usbank.com",
  "usbankcanada.com",
  "vanlanschot.com",
  "vanlanschot.nl",
  "vatican.va",
  "vbi.at",
  "vekselbanken.no",
  "venetobanca.it",
  "vestjyskbank.dk",
  "video.saxobank.com",
  "vontobel.com",
  "vpbank.com",
  "vpbank.lu",
  "wachovia.com",
  "wachoviasec.com",
  "wellsfargo.com",
  "westpac.co.nz",
  "westpac.com.au",
  "wgzbank.ie",
  "wilshirebank.com",
  "wir.ch",
  "wooribank.com",
  "wwsparbank.se",
  "ya.no",
  "ybonline.co.uk",
  "zkb.ch",
  "zugerkb.ch"
};

const int kEnableJavaByDefaultForTheseDomainsLength = 
  sizeof(kEnableJavaByDefaultForTheseDomains) /
    sizeof(kEnableJavaByDefaultForTheseDomains[0]);

// ReloadPluginInfoBarDelegate -------------------------------------------------

class ReloadPluginInfoBarDelegate : public ConfirmInfoBarDelegate {
 public:
  static void Create(InfoBarService* infobar_service,
                     content::NavigationController* controller,
                     const base::string16& message);

 private:
  ReloadPluginInfoBarDelegate(content::NavigationController* controller,
                              const base::string16& message);
  virtual ~ReloadPluginInfoBarDelegate();

  // ConfirmInfobarDelegate:
  virtual int GetIconID() const OVERRIDE;
  virtual base::string16 GetMessageText() const OVERRIDE;
  virtual int GetButtons() const OVERRIDE;
  virtual base::string16 GetButtonLabel(InfoBarButton button) const OVERRIDE;
  virtual bool Accept() OVERRIDE;

  content::NavigationController* controller_;
  base::string16 message_;
};

// static
void ReloadPluginInfoBarDelegate::Create(
    InfoBarService* infobar_service,
    content::NavigationController* controller,
    const base::string16& message) {
  infobar_service->AddInfoBar(
      ConfirmInfoBarDelegate::CreateInfoBar(scoped_ptr<ConfirmInfoBarDelegate>(
          new ReloadPluginInfoBarDelegate(controller, message))));
}

ReloadPluginInfoBarDelegate::ReloadPluginInfoBarDelegate(
    content::NavigationController* controller,
    const base::string16& message)
    : controller_(controller),
      message_(message) {}

ReloadPluginInfoBarDelegate::~ReloadPluginInfoBarDelegate(){ }

int ReloadPluginInfoBarDelegate::GetIconID() const {
  return IDR_INFOBAR_PLUGIN_CRASHED;
}

base::string16 ReloadPluginInfoBarDelegate::GetMessageText() const {
  return message_;
}

int ReloadPluginInfoBarDelegate::GetButtons() const {
  return BUTTON_OK;
}

base::string16 ReloadPluginInfoBarDelegate::GetButtonLabel(
    InfoBarButton button) const {
  DCHECK_EQ(BUTTON_OK, button);
  return l10n_util::GetStringUTF16(IDS_RELOAD_PAGE_WITH_PLUGIN);
}

bool ReloadPluginInfoBarDelegate::Accept() {
  controller_->Reload(true);
  return true;
}

}  // namespace

// PluginObserver -------------------------------------------------------------

#if defined(ENABLE_PLUGIN_INSTALLATION)
class PluginObserver::PluginPlaceholderHost : public PluginInstallerObserver {
 public:
  PluginPlaceholderHost(PluginObserver* observer,
                        int routing_id,
                        base::string16 plugin_name,
                        PluginInstaller* installer)
      : PluginInstallerObserver(installer),
        observer_(observer),
        routing_id_(routing_id) {
    DCHECK(installer);
    switch (installer->state()) {
      case PluginInstaller::INSTALLER_STATE_IDLE: {
        observer->Send(new ChromeViewMsg_FoundMissingPlugin(routing_id_,
                                                            plugin_name));
        break;
      }
      case PluginInstaller::INSTALLER_STATE_DOWNLOADING: {
        DownloadStarted();
        break;
      }
    }
  }

  // PluginInstallerObserver methods:
  virtual void DownloadStarted() OVERRIDE {
    observer_->Send(new ChromeViewMsg_StartedDownloadingPlugin(routing_id_));
  }

  virtual void DownloadError(const std::string& msg) OVERRIDE {
    observer_->Send(new ChromeViewMsg_ErrorDownloadingPlugin(routing_id_, msg));
  }

  virtual void DownloadCancelled() OVERRIDE {
    observer_->Send(new ChromeViewMsg_CancelledDownloadingPlugin(routing_id_));
  }

  virtual void DownloadFinished() OVERRIDE {
    observer_->Send(new ChromeViewMsg_FinishedDownloadingPlugin(routing_id_));
  }

 private:
  // Weak pointer; owns us.
  PluginObserver* observer_;

  int routing_id_;
};
#endif  // defined(ENABLE_PLUGIN_INSTALLATION)

PluginObserver::PluginObserver(content::WebContents* web_contents)
    : content::WebContentsObserver(web_contents),
      weak_ptr_factory_(this) {
}

PluginObserver::~PluginObserver() {
#if defined(ENABLE_PLUGIN_INSTALLATION)
  STLDeleteValues(&plugin_placeholders_);
#endif
}

void PluginObserver::RenderFrameCreated(
    content::RenderFrameHost* render_frame_host) {
#if defined(OS_WIN)
  // If the window belongs to the Ash desktop, before we navigate we need
  // to tell the renderview that NPAPI plugins are not supported so it does
  // not try to instantiate them. The final decision is actually done in
  // the IO thread by PluginInfoMessageFilter of this proces,s but it's more
  // complex to manage a map of Ash views in PluginInfoMessageFilter than
  // just telling the renderer via IPC.

  // TODO(shrikant): Implement solution which will help associate
  // render_view_host/webcontents/view/window instance with host desktop.
  // Refer to issue http://crbug.com/317940.
  // When non-active tabs are restored they are not added in view/window parent
  // hierarchy (chrome::CreateRestoredTab/CreateParams). Normally we traverse
  // parent hierarchy to identify containing desktop (like in function
  // chrome::GetHostDesktopTypeForNativeView).
  // Possible issue with chrome::GetActiveDesktop, is that it's global
  // state, which remembers last active desktop, which may break in scenarios
  // where we have instances on both Ash and Native desktop.

  // We will do both tests. Both have some factor of unreliability.
  aura::Window* window = web_contents()->GetNativeView();
  if (chrome::GetActiveDesktop() == chrome::HOST_DESKTOP_TYPE_ASH ||
      chrome::GetHostDesktopTypeForNativeView(window) ==
      chrome::HOST_DESKTOP_TYPE_ASH) {
    int routing_id = render_frame_host->GetRoutingID();
    render_frame_host->Send(new ChromeViewMsg_NPAPINotSupported(routing_id));
  }
#endif
}

void PluginObserver::PluginCrashed(const base::FilePath& plugin_path,
                                   base::ProcessId plugin_pid) {
  DCHECK(!plugin_path.value().empty());

  base::string16 plugin_name =
      PluginService::GetInstance()->GetPluginDisplayNameByPath(plugin_path);
  base::string16 infobar_text;
#if defined(OS_WIN)
  // Find out whether the plugin process is still alive.
  // Note: Although the chances are slim, it is possible that after the plugin
  // process died, |plugin_pid| has been reused by a new process. The
  // consequence is that we will display |IDS_PLUGIN_DISCONNECTED_PROMPT| rather
  // than |IDS_PLUGIN_CRASHED_PROMPT| to the user, which seems acceptable.
  base::ProcessHandle plugin_handle = base::kNullProcessHandle;
  bool open_result = base::OpenProcessHandleWithAccess(
      plugin_pid, PROCESS_QUERY_INFORMATION | SYNCHRONIZE, &plugin_handle);
  bool is_running = false;
  if (open_result) {
    is_running = base::GetTerminationStatus(plugin_handle, NULL) ==
        base::TERMINATION_STATUS_STILL_RUNNING;
    base::CloseProcessHandle(plugin_handle);
  }

  if (is_running) {
    infobar_text = l10n_util::GetStringFUTF16(IDS_PLUGIN_DISCONNECTED_PROMPT,
                                              plugin_name);
    UMA_HISTOGRAM_COUNTS("Plugin.ShowDisconnectedInfobar", 1);
  } else {
    infobar_text = l10n_util::GetStringFUTF16(IDS_PLUGIN_CRASHED_PROMPT,
                                              plugin_name);
    UMA_HISTOGRAM_COUNTS("Plugin.ShowCrashedInfobar", 1);
  }
#else
  // Calling the POSIX version of base::GetTerminationStatus() may affect other
  // code which is interested in the process termination status. (Please see the
  // comment of the function.) Therefore, a better way is needed to distinguish
  // disconnections from crashes.
  infobar_text = l10n_util::GetStringFUTF16(IDS_PLUGIN_CRASHED_PROMPT,
                                            plugin_name);
  UMA_HISTOGRAM_COUNTS("Plugin.ShowCrashedInfobar", 1);
#endif

  ReloadPluginInfoBarDelegate::Create(
      InfoBarService::FromWebContents(web_contents()),
      &web_contents()->GetController(),
      infobar_text);
}

bool PluginObserver::OnMessageReceived(const IPC::Message& message) {
  IPC_BEGIN_MESSAGE_MAP(PluginObserver, message)
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_BlockedOutdatedPlugin,
                        OnBlockedOutdatedPlugin)
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_BlockedUnauthorizedPlugin,
                        OnBlockedUnauthorizedPlugin)
#if defined(ENABLE_PLUGIN_INSTALLATION)
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_FindMissingPlugin,
                        OnFindMissingPlugin)
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_RemovePluginPlaceholderHost,
                        OnRemovePluginPlaceholderHost)
#endif
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_OpenAboutPlugins,
                        OnOpenAboutPlugins)
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_CouldNotLoadPlugin,
                        OnCouldNotLoadPlugin)
    IPC_MESSAGE_HANDLER(ChromeViewHostMsg_NPAPINotSupported,
                        OnNPAPINotSupported)

    IPC_MESSAGE_UNHANDLED(return false)
  IPC_END_MESSAGE_MAP()

  return true;
}

void PluginObserver::OnBlockedUnauthorizedPlugin(
    const base::string16& name,
    const std::string& identifier) {
  std::string name_utf8 = base::UTF16ToUTF8(name);
  if (name_utf8 == PluginMetadata::kJavaGroupName) {
    content::WebContents* contents = web_contents();
    if (contents) {
      GURL url = contents->GetURL();
      for (int i = 0; i < kEnableJavaByDefaultForTheseDomainsLength; i++) {
        if (url.DomainIs(kEnableJavaByDefaultForTheseDomains[i])) {
          contents->Send(new ChromeViewMsg_LoadBlockedPlugins(
            contents->GetRoutingID(), identifier));
          return;
        }
      }
    }
  }

  UnauthorizedPluginInfoBarDelegate::Create(
      InfoBarService::FromWebContents(web_contents()),
      Profile::FromBrowserContext(web_contents()->GetBrowserContext())->
          GetHostContentSettingsMap(),
      name, identifier);
}

void PluginObserver::OnBlockedOutdatedPlugin(int placeholder_id,
                                             const std::string& identifier) {
#if defined(ENABLE_PLUGIN_INSTALLATION)
  PluginFinder* finder = PluginFinder::GetInstance();
  // Find plugin to update.
  PluginInstaller* installer = NULL;
  scoped_ptr<PluginMetadata> plugin;
  if (finder->FindPluginWithIdentifier(identifier, &installer, &plugin)) {
    plugin_placeholders_[placeholder_id] = new PluginPlaceholderHost(
        this, placeholder_id, plugin->name(), installer);
    OutdatedPluginInfoBarDelegate::Create(InfoBarService::FromWebContents(
        web_contents()), installer, plugin.Pass());
  } else {
    NOTREACHED();
  }
#else
  // If we don't support third-party plug-in installation, we shouldn't have
  // outdated plug-ins.
  NOTREACHED();
#endif  // defined(ENABLE_PLUGIN_INSTALLATION)
}

#if defined(ENABLE_PLUGIN_INSTALLATION)
void PluginObserver::OnFindMissingPlugin(int placeholder_id,
                                         const std::string& mime_type) {
  std::string lang = "en-US";  // Oh yes.
  scoped_ptr<PluginMetadata> plugin_metadata;
  PluginInstaller* installer = NULL;
  bool found_plugin = PluginFinder::GetInstance()->FindPlugin(
      mime_type, lang, &installer, &plugin_metadata);
  if (!found_plugin) {
    Send(new ChromeViewMsg_DidNotFindMissingPlugin(placeholder_id));
    return;
  }
  DCHECK(installer);
  DCHECK(plugin_metadata.get());

  plugin_placeholders_[placeholder_id] =
      new PluginPlaceholderHost(this, placeholder_id, plugin_metadata->name(),
                                installer);
  PluginInstallerInfoBarDelegate::Create(
      InfoBarService::FromWebContents(web_contents()), installer,
      plugin_metadata.Pass(),
      base::Bind(&PluginObserver::InstallMissingPlugin,
                 weak_ptr_factory_.GetWeakPtr(), installer));
}

void PluginObserver::InstallMissingPlugin(
    PluginInstaller* installer,
    const PluginMetadata* plugin_metadata) {
  if (plugin_metadata->url_for_display()) {
    installer->OpenDownloadURL(plugin_metadata->plugin_url(), web_contents());
  } else {
    TabModalConfirmDialog::Create(
        new ConfirmInstallDialogDelegate(
            web_contents(), installer, plugin_metadata->Clone()),
        web_contents());
  }
}

void PluginObserver::OnRemovePluginPlaceholderHost(int placeholder_id) {
  std::map<int, PluginPlaceholderHost*>::iterator it =
      plugin_placeholders_.find(placeholder_id);
  if (it == plugin_placeholders_.end()) {
    NOTREACHED();
    return;
  }
  delete it->second;
  plugin_placeholders_.erase(it);
}
#endif  // defined(ENABLE_PLUGIN_INSTALLATION)

void PluginObserver::OnOpenAboutPlugins() {
  web_contents()->OpenURL(OpenURLParams(
      GURL(chrome::kChromeUIPluginsURL),
      content::Referrer(web_contents()->GetURL(),
                        blink::WebReferrerPolicyDefault),
      NEW_FOREGROUND_TAB, content::PAGE_TRANSITION_AUTO_BOOKMARK, false));
}

void PluginObserver::OnCouldNotLoadPlugin(const base::FilePath& plugin_path) {
  g_browser_process->metrics_service()->LogPluginLoadingError(plugin_path);
  base::string16 plugin_name =
      PluginService::GetInstance()->GetPluginDisplayNameByPath(plugin_path);
  SimpleAlertInfoBarDelegate::Create(
      InfoBarService::FromWebContents(web_contents()),
      IDR_INFOBAR_PLUGIN_CRASHED,
      l10n_util::GetStringFUTF16(IDS_PLUGIN_INITIALIZATION_ERROR_PROMPT,
                                 plugin_name),
      true);
}

void PluginObserver::OnNPAPINotSupported(const std::string& identifier) {
#if defined(OS_WIN) && defined(ENABLE_PLUGIN_INSTALLATION)
#if !defined(USE_AURA)
  DCHECK(base::win::IsMetroProcess());
#endif

  Profile* profile =
      Profile::FromBrowserContext(web_contents()->GetBrowserContext());
  if (profile->IsOffTheRecord())
    return;
  HostContentSettingsMap* content_settings =
      profile->GetHostContentSettingsMap();
  if (content_settings->GetContentSetting(
      web_contents()->GetURL(),
      web_contents()->GetURL(),
      CONTENT_SETTINGS_TYPE_METRO_SWITCH_TO_DESKTOP,
      std::string()) == CONTENT_SETTING_BLOCK)
    return;

  scoped_ptr<PluginMetadata> plugin;
  bool ret = PluginFinder::GetInstance()->FindPluginWithIdentifier(
      identifier, NULL, &plugin);
  DCHECK(ret);

  PluginMetroModeInfoBarDelegate::Create(
      InfoBarService::FromWebContents(web_contents()),
      PluginMetroModeInfoBarDelegate::DESKTOP_MODE_REQUIRED, plugin->name());
#endif
}
