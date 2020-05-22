#include <Python.h>
#ifdef _WIN32
#include <Windows.h>
#include <propsys.h>
#include <propkey.h>
#include <propvarutil.h>

// Hack to get the handle to the current DLL we are in
// https://devblogs.microsoft.com/oldnewthing/20041025-00/?p=37483
EXTERN_C IMAGE_DOS_HEADER __ImageBase;
#define THIS_DLL_HANDLE ((HINSTANCE)&__ImageBase)

WCHAR global_appid[1024] = L"<no-appid-set>";

void CALLBACK HandleWinEvent(
    HWINEVENTHOOK hook,
    DWORD event,
    HWND hwnd, 
    LONG idObject,
    LONG idChild, 
    DWORD dwEventThread,
    DWORD dwmsEventTime
){
    HRESULT hr;
    PROPVARIANT pv;
    IPropertyStore *store;
    if (idObject == OBJID_WINDOW){
        hr = SHGetPropertyStoreForWindow(hwnd, IID_PPV_ARGS(&store));
        if (!SUCCEEDED(hr)){return;}
        switch (event){
            case EVENT_OBJECT_CREATE:
                hr = InitPropVariantFromString(global_appid, &pv);
                if (!SUCCEEDED(hr)){return;}
                break;
            case EVENT_OBJECT_DESTROY:
                PropVariantInit(&pv);
                break;
        }
        hr = store->SetValue(PKEY_AppUserModel_ID, pv);
        if (!SUCCEEDED(hr)){return;}
        PropVariantClear(&pv);
        store->Release();
    }
}

static PyObject *
sethook(PyObject *self, PyObject *args){
    PyObject *appid;
    HWINEVENTHOOK hookhandle;
    if (!PyArg_ParseTuple(args, "O", &appid)){
        return NULL;
    }
    PyUnicode_AsWideChar(appid, global_appid, 1024);
    hookhandle = SetWinEventHook(
        EVENT_OBJECT_CREATE,
        EVENT_OBJECT_CREATE,
        THIS_DLL_HANDLE,
        HandleWinEvent,
        GetCurrentProcessId(),
        0,
        WINEVENT_INCONTEXT
    );
    hookhandle = SetWinEventHook(
        EVENT_OBJECT_DESTROY,
        EVENT_OBJECT_DESTROY,
        THIS_DLL_HANDLE,
        HandleWinEvent,
        GetCurrentProcessId(),
        0,
        WINEVENT_INCONTEXT
    );
    Py_RETURN_NONE;
}
#endif

static PyMethodDef wineventhook_methods[] = {
#ifdef _WIN32
    {"sethook",sethook, METH_VARARGS, "Enable a hook to set window AppUserModelIDs"},
#endif
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef wineventhook = {
    PyModuleDef_HEAD_INIT, "wineventhook", "", -1, wineventhook_methods
};


PyMODINIT_FUNC PyInit_wineventhook(void){
    return PyModule_Create(&wineventhook);
}