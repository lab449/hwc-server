# MATLAB client for HDU DSS

Download the maintained client from http://dss.hdu.vedyakov.com/clients/hwc-matlab-client.zip, extract it into a working directory and run:

```matlab
chdu = hwc_connect();
```

Keep `auth_config.json` when replacing client files. If an old HWC object is loaded after an update, run `clear chdu` and reconnect. Normal HDU IDs remain numeric: any positive whole number of the existing ID length is accepted, without the old admission-year range. ID strings or a new wire protocol are not required.

HTTP is the default connection for all clients. The server also supports HTTPS when an HTTPS URL is supplied. The selected URL is used for updates, login, task requests, answer submissions and task-file downloads. Both protocols use a 30-second response timeout. HTTPS retains MATLAB's default certificate verification.

These files are maintained with this server and copied into the image at build time. Startup does not pull a different client from GitHub. Version endpoints describe the exact files served by the application. The updater downloads all client files into a temporary directory over the selected HTTP or HTTPS connection, checks the HWC/launcher version hashes, then installs them; credentials are preserved.

Source provenance: ITMORobotics/hwc-matlab-client, revision `23b157f28841029a3b76efb00110a6148cf7c118`, copied from the previously deployed image. Maintained changes cover TLS, numeric ID validation, updates and task-file downloads.

Optional native MATLAB checks (from the repository root):

```matlab
addpath('matlab');
assertSuccess(runtests('matlab/tests'));
```
