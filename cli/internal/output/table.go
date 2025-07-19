package output

import (
	"fmt"
	"reflect"
	"strings"
	"time"

	"github.com/olekukonko/tablewriter"
)

func formatAsTable(data interface{}) (string, error) {
	if data == nil {
		return "", nil
	}

	val := reflect.ValueOf(data)
	if val.Kind() == reflect.Ptr {
		val = val.Elem()
	}

	switch val.Kind() {
	case reflect.Slice:
		return formatSliceAsTable(val)
	case reflect.Struct:
		return formatStructAsTable(val)
	case reflect.Map:
		return formatMapAsTable(val)
	default:
		return fmt.Sprintf("%v\n", data), nil
	}
}

func formatSliceAsTable(val reflect.Value) (string, error) {
	if val.Len() == 0 {
		return "No data available\n", nil
	}

	firstItem := val.Index(0)
	if firstItem.Kind() == reflect.Ptr {
		firstItem = firstItem.Elem()
	}

	if firstItem.Kind() != reflect.Struct {
		return formatSimpleSlice(val), nil
	}

	var buf strings.Builder
	table := tablewriter.NewWriter(&buf)

	headers := extractStructHeaders(firstItem.Type())
	table.SetHeader(headers)

	for i := 0; i < val.Len(); i++ {
		item := val.Index(i)
		if item.Kind() == reflect.Ptr {
			item = item.Elem()
		}
		row := extractStructValues(item)
		table.Append(row)
	}

	table.Render()
	return buf.String(), nil
}

func formatStructAsTable(val reflect.Value) (string, error) {
	var buf strings.Builder
	table := tablewriter.NewWriter(&buf)

	table.SetHeader([]string{"Field", "Value"})

	typ := val.Type()
	for i := 0; i < val.NumField(); i++ {
		field := typ.Field(i)
		if !field.IsExported() {
			continue
		}

		fieldName := getFieldDisplayName(field)
		fieldValue := formatFieldValue(val.Field(i))
		table.Append([]string{fieldName, fieldValue})
	}

	table.Render()
	return buf.String(), nil
}

func formatMapAsTable(val reflect.Value) (string, error) {
	var buf strings.Builder
	table := tablewriter.NewWriter(&buf)

	table.SetHeader([]string{"Key", "Value"})

	for _, key := range val.MapKeys() {
		value := val.MapIndex(key)
		table.Append([]string{
			fmt.Sprintf("%v", key.Interface()),
			formatFieldValue(value),
		})
	}

	table.Render()
	return buf.String(), nil
}

func formatSimpleSlice(val reflect.Value) string {
	var items []string
	for i := 0; i < val.Len(); i++ {
		items = append(items, fmt.Sprintf("%v", val.Index(i).Interface()))
	}
	return strings.Join(items, "\n") + "\n"
}

func extractStructHeaders(typ reflect.Type) []string {
	var headers []string
	for i := 0; i < typ.NumField(); i++ {
		field := typ.Field(i)
		if !field.IsExported() {
			continue
		}
		headers = append(headers, getFieldDisplayName(field))
	}
	return headers
}

func extractStructValues(val reflect.Value) []string {
	var values []string
	for i := 0; i < val.NumField(); i++ {
		field := val.Type().Field(i)
		if !field.IsExported() {
			continue
		}
		values = append(values, formatFieldValue(val.Field(i)))
	}
	return values
}

func getFieldDisplayName(field reflect.StructField) string {
	jsonTag := field.Tag.Get("json")
	if jsonTag != "" && jsonTag != "-" {
		name := strings.Split(jsonTag, ",")[0]
		if name != "" {
			return strings.ReplaceAll(strings.ToTitle(name), "_", " ")
		}
	}
	return field.Name
}

func formatFieldValue(val reflect.Value) string {
	if !val.IsValid() {
		return ""
	}

	switch val.Kind() {
	case reflect.Ptr:
		if val.IsNil() {
			return ""
		}
		return formatFieldValue(val.Elem())
	case reflect.String:
		return val.String()
	case reflect.Bool:
		if val.Bool() {
			return "✓"
		}
		return "✗"
	case reflect.Slice:
		if val.Len() == 0 {
			return ""
		}
		var items []string
		for i := 0; i < val.Len(); i++ {
			items = append(items, formatFieldValue(val.Index(i)))
		}
		return strings.Join(items, ", ")
	case reflect.Struct:
		if val.Type() == reflect.TypeOf(time.Time{}) {
			t := val.Interface().(time.Time)
			if t.IsZero() {
				return ""
			}
			return t.Format("2006-01-02 15:04:05")
		}
		return fmt.Sprintf("%v", val.Interface())
	default:
		return fmt.Sprintf("%v", val.Interface())
	}
}
