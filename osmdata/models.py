from __future__ import unicode_literals

import re

from django.contrib.gis.db import models

from .geo_utils import planify_coords


class Bounds(models.Model):
    minlat = models.FloatField()
    minlon = models.FloatField()
    maxlat = models.FloatField()
    maxlon = models.FloatField()


class OSMElement(models.Model):
    NODE = 'node'
    RELATION = 'relation'
    WAY = 'way'

    SUBTYPES = (NODE, RELATION, WAY)

    osmid = models.PositiveIntegerField(null=True)
    version = models.PositiveIntegerField(null=True)
    timestamp = models.DateTimeField(null=True)
    uid = models.PositiveIntegerField(null=True)
    user = models.CharField(blank=True, max_length=255)
    changeset = models.PositiveIntegerField(null=True)
    bounds = models.OneToOneField(
        Bounds,
        null=True, blank=True, on_delete=models.PROTECT)
    visible = models.BooleanField(default=True)

    def specialized(self):
        return getattr(self, self.type())

    def type(self):
        for i in self.SUBTYPES:
            if hasattr(self, i):
                return i
        raise ValueError('{} must be of one of those subtypes {}'.format(self, self.SUBTYPES))

    def tags_dict(self):
        """Returns the element tags as a python primitive dict

        Usefull for in-python comparison with another tag list

        :return: a list of key,value couples
        """
        return {k: v for k,v in self.tags.values_list('k', 'v')}

    def __str__(self):
        return '<{} id="{}">'.format(self.__class__.__name__, self.osmid)


class Tag(models.Model):
    element = models.ForeignKey(OSMElement, related_name='tags', on_delete=models.CASCADE)
    k = models.CharField(max_length=255)
    v = models.CharField(max_length=255)

    RE_TAG_PATTERN = re.compile(r'(?P<key>.+)=(?P<value>.+)')

    @classmethod
    def split_tag_pattern(cls, multi_tag_pattern):
        """
        :param multiple tag_pattern: a comma-separated tag patterns
          ex: foo=bar,spam=*
        :return a list of strings containing each one part of the pattern.
        """
        return multi_tag_pattern.split(',')

    @classmethod
    def parse_tag_pattern(cls, tag_pattern):
        """ Parse osm tag filter pattern

        tag_pattern examples: "amenity=bench", "highway=*"

        :param tag_pattern: a osm-style tag filter
        :return: a dict to filter fields on key and optionaly value
          eg:
            - {"k": "highway", "v": "primary"}
            - {"k": "highway"}
        """
        m = cls.RE_TAG_PATTERN.match(tag_pattern)
        if m:
            key, value = m.group('key'), m.group('value')
            _filter = {'k': key}
            if value != '*':
                _filter['v'] = value
        else:
            raise ValueError('Invalid tag pattern : "{}"'.format(
                tag_pattern))
        return _filter

    def match(self, tag_pattern):
        """ Match according osm tags syntax

        :param tag_pattern: an osm-style tag filter
        :return: True if the tag matches the spec, False else
        """
        filter_spec = self.parse_tag_pattern(tag_pattern)

        for model_field_name, model_field_value in filter_spec.items():
            if getattr(self, model_field_name) != model_field_value:
                return False

        return True

    def __str__(self):
        return '{}={}'.format(self.k, self.v)

class Node(OSMElement):
    lat = models.FloatField(null=True) # FIXME ; could be validated better
    lon = models.FloatField(null=True)
    # projected coordinates. Otherwise, spatialite is not able to make distance math
    latlon = models.PointField(srid=3857, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.lat and self.lon:
            self.latlon = planify_coords(float(self.lat), float(self.lon))
        return super().save(*args, **kwargs)


class Way(OSMElement):
    nodes = models.ManyToManyField(Node, through='WayNode')

    def nodes_list(self):
        """ Returns the nodes as a primitive ordered list
        """
        return self.nodes.values_list('osmid', 'lat', 'lon')

class WayNode(models.Model):
    way = models.ForeignKey(Way, on_delete=models.CASCADE)
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()


class Relation(OSMElement):
    pass
    # members = models.ManyToManyField(
    #     OSMElement, through='RelationMember', related_name='parent_relation')



class RelationMember(models.Model):
    relation = models.ForeignKey(Relation, related_name='members', on_delete=models.CASCADE)
    element = models.ForeignKey(OSMElement, related_name='related_element', on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    role = models.CharField(max_length=255, blank=True)


class Action(models.Model):
    CREATE = 'create'
    MODIFY = 'modify'
    DELETE = 'delete'
    REMOVE = 'remove'

    type = models.CharField(
        max_length=10, choices=(
            (REMOVE, REMOVE),
            (DELETE, DELETE),
            (MODIFY, MODIFY),
            (CREATE, CREATE)))

    new = models.OneToOneField(
        OSMElement,
        related_name='new_for', null=True, on_delete=models.PROTECT)
    old = models.OneToOneField(
        OSMElement,
        related_name='old_for', null=True, on_delete=models.PROTECT)

class Diff(models.Model):
    actions = models.ManyToManyField(Action)
    import_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Diff #{}'.format(self.pk)
