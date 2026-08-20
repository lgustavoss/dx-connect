package br.com.deskrudder.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(UnifiedPushPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
