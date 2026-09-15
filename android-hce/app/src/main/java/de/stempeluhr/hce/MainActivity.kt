package de.stempeluhr.hce

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity:Activity(){
 override fun onCreate(savedInstanceState:Bundle?){
  super.onCreate(savedInstanceState);val prefs=getSharedPreferences("stempeluhr_mobile",MODE_PRIVATE)
  val title=TextView(this).apply{text="Stempeluhr NFC v2";textSize=28f}
  val info=TextView(this).apply{text=if(prefs.contains("device_token")&&prefs.contains("credential_id"))"Smartphone ist gekoppelt und HCE v2 bereit." else "Pairing-Daten eintragen."}
  val credential=EditText(this).apply{hint="Credential-ID";inputType=2}
  val token=EditText(this).apply{hint="Geräte-Token";setSingleLine(false)}
  val save=Button(this).apply{text="Kopplung speichern"};val clear=Button(this).apply{text="Kopplung entfernen"}
  save.setOnClickListener{val id=credential.text.toString().trim();val value=token.text.toString().trim();if(id.isNotEmpty()&&value.isNotEmpty()){prefs.edit().putString("credential_id",id).putString("device_token",value).apply();credential.text.clear();token.text.clear();info.text="Smartphone ist gekoppelt. Der Geräte-Token wird bei NFC nicht übertragen."}}
  clear.setOnClickListener{prefs.edit().clear().apply();info.text="Kopplung entfernt."}
  val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(40,70,40,40);addView(title);addView(info);addView(credential);addView(token);addView(save);addView(clear)};setContentView(root)
 }
}
