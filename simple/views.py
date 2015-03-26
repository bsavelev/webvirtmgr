from libvirt import libvirtError
from django.http import HttpResponseRedirect
from django.http import Http404
from django.views.generic import FormView
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from instance.views import InstanceList
from create.forms import NewVMForm
from instance.models import Instance
from servers.models import Compute
from vrtManager import util
from vrtManager.create import wvmCreate


class MyInstanceList(InstanceList):
    template_name = 'simple/instances.html'

    def get_instances(self):
        l = super(MyInstanceList, self).get_instances()
        r = []
        for i, item in enumerate(l):
            line = 'user-%d-' % self.request.user.pk
            if item['name'].startswith(line):
                r.append(item)
        return r


class CreateInstanceFromTemplate(FormView):
    conn = None
    compute = None
    errors = []
    form_class = NewVMForm
    template_name = 'simple/create.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseRedirect(reverse('login'))
        host_id = kwargs.get('host_id')
        if not host_id:
            raise Http404
        compute = Compute.objects.get(id=host_id)
        try:
            self.conn = wvmCreate(
                compute.hostname,
                compute.login,
                compute.password,
                compute.type)
        except libvirtError as err:
            self.errors.append(err)
        self.compute = compute
        return super(CreateInstanceFromTemplate, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.conn:
            raise IOError('Fail to connect to libvirt')
        volumes = {}
        errors = []
        conn = self.conn
        meta_prealloc = False
        meta_base = False
        instances = conn.get_instances()
        data = form.cleaned_data
        name = "user-%d-%s" % (self.request.user.pk, data['name'])
        if data['meta_prealloc']:
            meta_prealloc = True
        if data['meta_base']:
            meta_base = True
        if instances:
            if name in instances:
                msg = _("A virtual machine with this name already exists")
                errors.append(msg)
        if not errors:
            if data['hdd_size']:
                if not data['mac']:
                    msg = _("No Virtual Machine MAC has been entered")
                    errors.append(msg)
                else:
                    try:
                        path = conn.create_volume(data['storage'], name, data['hdd_size'],
                                                  metadata=meta_prealloc)
                        volumes[path] = conn.get_volume_type(path)
                    except libvirtError as msg_error:
                        errors.append(msg_error.message)
            elif data['template']:
                templ_path = conn.get_volume_path(data['template'])
                clone_path = conn.clone_from_template(name, templ_path, metadata=meta_prealloc, meta_base=meta_base)
                volumes[clone_path] = conn.get_volume_type(clone_path)
            else:
                if not data['images']:
                    msg = _("First you need to create or select an image")
                    errors.append(msg)
                else:
                    for vol in data['images'].split(','):
                        try:
                            path = conn.get_volume_path(vol)
                            volumes[path] = conn.get_volume_type(path)
                        except libvirtError as msg_error:
                            errors.append(msg_error.message)
            if not errors:
                uuid = util.randomUUID()
                try:
                    conn.create_instance(name, data['memory'], data['vcpu'], data['host_model'],
                                         uuid, volumes, data['networks'], data['virtio'], data['mac'])
                    create_instance = Instance(compute=self.compute, name=name, uuid=uuid)
                    create_instance.save()
                except libvirtError as err:
                    if data['hdd_size']:
                        conn.delete_volume(volumes.keys()[0])
                    errors.append(err)
        return super(CreateInstanceFromTemplate, self).form_valid(form)

    def get_success_url(self):
        r = reverse('my_instance_list')
        return r

    def get_context_data(self, **kwargs):
        context = super(CreateInstanceFromTemplate, self).get_context_data(**kwargs)
        c = {
            'get_images': sorted(self.conn.get_storages_images()),
            'errors': self.errors,
            'compute': self.compute,
            'request': self.request,
        }
        context.update(c)
        return context
