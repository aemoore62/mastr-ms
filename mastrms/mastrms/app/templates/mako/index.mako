<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<!--
 * This file is part of Madas.
 *
 * Madas is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Madas is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Madas.  If not, see <http://www.gnu.org/licenses/>.
 *
 -->
    <title>MA LIMS</title>

<link rel="shortcut icon" href="/favicon.ico" />
<link rel="stylesheet" href="${wh.url('/static/ext-3.4.0/resources/css/ext-all.css')}"/>
<link rel="stylesheet" type="text/css" href="${wh.url('/static/css/main.css')}"/>
<link rel="stylesheet" href="${wh.url('/static/css/RowEditor.css')}"/>
<link rel="stylesheet" type="text/css" href="${wh.url('/static/css/file-upload.css')}"/>
<!--
<script type="text/javascript" src="${wh.url('/static/js/repo/scriptaculous/scriptaculous.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/prototype.js')}"></script>
<script src="${wh.url('/static/ext-3.4.0/adapter/ext/ext-base.js')}" type="text/javascript"></script>
<script src="${wh.url('/static/ext-3.4.0/adapter/prototype/ext-prototype-adapter.js')}" type="text/javascript"></script>
<script src="${wh.url('/static/ext-3.3.0/ext-all.js')}"></script>
-->
<script type="text/javascript" src="${wh.url('/static/js/repo/prototype.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/scriptaculous/scriptaculous.js')}"></script>
<script src="${wh.url('/static/ext-3.4.0/adapter/ext/ext-base-debug.js')}" type="text/javascript"></script>
<!--<script src="${wh.url('/static/ext-3.4.0/adapter/ext/ext-base.js')}" type="text/javascript"></script>-->
<script src="${wh.url('/static/ext-3.4.0/ext-all-debug.js')}"></script>
<!--<script src="${wh.url('/static/ext-3.4.0/ext-all.js')}"></script>-->
<script type="text/javascript" src="${wh.url('/static/js/repo/DisplayField.js')}"></script>

<!-- setup variable -->
<script>
Ext.ns('MA', 'MA.Dashboard', 'MA.Utils');
MA.BaseUrl = '${ APP_SECURE_URL }';
if(Ext.isIE6 || Ext.isIE7 || Ext.isAir){ Ext.BLANK_IMAGE_URL = "${wh.url('/static/images/default/s.gif')}"; }
</script>

<!-- Madas scripts -->
<script type="text/javascript" src="${wh.url('/static/js/FieldLabeler.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/utils.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/global.js')}"></script>

<script type="text/javascript" src="${wh.url('/static/js/json2.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/datastores.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/renderers.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/GridSearch.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/MARowEditor.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/FileUploadField.js')}"></script>



<script type="text/javascript" src="${wh.url('/static/js/repo/samples.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/tracking.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/biosource.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/treatment.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/sampleprep.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/access.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/files.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/runs.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/runlist.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/rulegenerators.js')}"></script>

<script type="text/javascript" src="${wh.url('/static/js/repo/projects.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/repo/clients.js')}"></script>

<script type="text/javascript" src="${wh.url('/static/js/datastores.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/menu.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/registration.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/login.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/controller.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/dashboard.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/admin.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/user.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/quote.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/swfobject.js')}"></script>
<script type="text/javascript" src="${wh.url('/static/js/screencasts.js')}"></script>
<script>
var callbackCount = 0;
function callbacker(){
    var username = document.getElementById('username').value;
    
    if (username == "" && callbackCount < 5) {
        //console.log("waiting...");
        callbackCount += 1;
        window.setTimeout("callbacker();", 100);
        return;
    }
    
    MA.InitApplication('${ APP_SECURE_URL }', '${ username }', '${ mainContentFunction }', '${ params }');
    document.getElementById("appLoad").style.display = "none";
    //document.getElementById('loginDiv').style.display = 'none';
}
</script>

</head>
<body onLoad="callbacker();">

<div id="north"><div id="appTitle">MA LIMS</div><div id="toolbar"></div></div>

<div id="south">(c) CCG 2009-2012</div>


<div style="position:relative;">
<div id="appLoad" style="z-index:1;position:absolute;left:0px;top:0px;width:400px;height:200px;background:white;padding:200px;"><img src="${wh.url('static/ext-3.4.0/resources/images/default/shared/large-loading.gif')}"> Loading...</div>
<div id="loginDiv" style="width:300;">
<form id="loginForm" action="${wh.url('/login/processLogin')}" method="POST">
<label class="x-form-item-label">Email address:</label>
<div class="x-form-element" style="margin-top:-10px;">
<input id="username" name="username">
</div>
<div class="x-form-clear-left">
</div>
<label class="x-form-item-label">Password:</label>
<div class="x-form-element" style="margin-top:-10px;">
<input id="password" name="password" type="password">
</div>
<div class="x-form-clear-left">
</div>
<input type="submit" value="Login" style="margin-left:200px;">
</form>
</div>

<div id="centerDiv"></div>



<form id="hiddenForm"></form>

</body>
</html>